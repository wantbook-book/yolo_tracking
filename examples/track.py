# https://github.com/ultralytics/ultralytics/issues/1429#issuecomment-1519239409
import math
import json
import os.path as osp
from pytorch_openpose.src import util
from pytorch_openpose.src.body import Body
from pytorch_openpose.src.hand import Hand
from pathlib import Path
import torch
import argparse
import numpy as np
import cv2
from types import SimpleNamespace

from boxmot.tracker_zoo import create_tracker
from ultralytics.yolo.engine.model import YOLO, TASK_MAP

from ultralytics.yolo.utils import LOGGER, SETTINGS, colorstr, ops, is_git_dir, IterableSimpleNamespace
from ultralytics.yolo.utils.checks import check_imgsz, print_args
from ultralytics.yolo.utils.files import increment_path
from ultralytics.yolo.engine.results import Boxes
from ultralytics.yolo.data.utils import VID_FORMATS

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0].parents[0]  # repo root absolute path
EXAMPLES = FILE.parents[0]  # examples absolute path
WEIGHTS = EXAMPLES / 'weights'

body_estimation = Body('pytorch_openpose/model/body_pose_model.pth')
hand_estimation = Hand('pytorch_openpose/model/hand_pose_model.pth')
def on_predict_start(predictor):
    predictor.trackers = []
    predictor.tracker_outputs = [None] * predictor.dataset.bs
    predictor.args.tracking_config = \
        ROOT /\
        'boxmot' /\
        opt.tracking_method /\
        'configs' /\
        (opt.tracking_method + '.yaml')
    for i in range(predictor.dataset.bs):
        tracker = create_tracker(
            predictor.args.tracking_method,
            predictor.args.tracking_config,
            predictor.args.reid_model,
            predictor.device,
            predictor.args.half
        )
        predictor.trackers.append(tracker)
                
                
def write_MOT_results(txt_path, results, frame_idx, i):
    nr_dets = len(results.boxes)
    frame_idx = torch.full((1, 1), frame_idx + 1)
    frame_idx = frame_idx.repeat(nr_dets, 1)
    dont_care = torch.full((nr_dets, 3), -1)
    i = torch.full((nr_dets, 1), i)
    mot = torch.cat([
        frame_idx,
        results.boxes.id.unsqueeze(1).to('cpu'),
        ops.xyxy2ltwh(results.boxes.xyxy).to('cpu'),
        dont_care,
        i
    ], dim=1)

    with open(str(txt_path) + '.txt', 'ab') as f:  # append binary mode
        np.savetxt(f, mot.numpy(), fmt='%d')  # save as ints instead of scientific notation


def write_json_results(json_path, boxes, frame_idx, candidates, subsets):
    if not osp.exists(str(json_path)+'.json'):
        with open(str(json_path)+'.json', 'w') as f:
            json.dump([], f, indent=4)
    with open(str(json_path)+'.json', 'r') as f:
        data = json.load(f)
    people = []
    for box, candidate, subset in zip(boxes, candidates, subsets):
        xyxy = [i for i in box.xyxy[0]]
        id = int(box.id[0])
        pose_points = []
        for i in range(18):
            for n in range(len(subset)):
                index = int(subset[n][i])
                if index == -1:
                    if n == len(subset)-1:
                        pose_points.append([0,0])
                    continue
                x, y = candidate[index][0:2]
                pose_points.append([x,y])
        people.append(
            {
                'id': id,
                'xyxy': xyxy,
                'pose_points': pose_points
            }
        )
    output = {
        'frame_idx':frame_idx,
        'people': people
    }
    data.append(output)
    with open(str(json_path)+'.json', 'w') as f:
        json.dump(data, f, indent=4)


@torch.no_grad()
def run(args):
    
    model = YOLO(args['yolo_model'])
    overrides = model.overrides.copy()
    model.predictor = TASK_MAP[model.task][3](overrides=overrides, _callbacks=model.callbacks)
    
    # extract task predictor
    predictor = model.predictor

    # combine default predictor args with custom, preferring custom
    combined_args = {**predictor.args.__dict__, **args}
    # overwrite default args
    predictor.args = IterableSimpleNamespace(**combined_args)

    # setup source and model
    if not predictor.model:
        predictor.setup_model(model=model.model, verbose=False)
    predictor.setup_source(predictor.args.source)
    
    predictor.args.imgsz = check_imgsz(predictor.args.imgsz, stride=model.model.stride, min_dim=2)  # check image size
    predictor.save_dir = increment_path(Path(predictor.args.project) / predictor.args.name, exist_ok=predictor.args.exist_ok)
    
    # Check if save_dir/ label file exists
    if predictor.args.save or predictor.args.save_txt or predictor.args.save_json:
        (predictor.save_dir / 'labels' if predictor.args.save_txt else predictor.save_dir).mkdir(parents=True, exist_ok=True)
    # Warmup model
    if not predictor.done_warmup:
        predictor.model.warmup(imgsz=(1 if predictor.model.pt or predictor.model.triton else predictor.dataset.bs, 3, *predictor.imgsz))
        predictor.done_warmup = True
    predictor.seen, predictor.windows, predictor.batch, predictor.profilers = 0, [], None, (ops.Profile(), ops.Profile(), ops.Profile(), ops.Profile(), ops.Profile())
    predictor.add_callback('on_predict_start', on_predict_start)
    
    predictor.run_callbacks('on_predict_start')
    for frame_idx, batch in enumerate(predictor.dataset):
        predictor.run_callbacks('on_predict_batch_start')
        predictor.batch = batch
        path, im0s, vid_cap, s = batch
        visualize = increment_path(save_dir / Path(path[0]).stem, exist_ok=True, mkdir=True) if predictor.args.visualize and (not predictor.dataset.source_type.tensor) else False

        # Preprocess
        with predictor.profilers[0]:
            im = predictor.preprocess(im0s)

        # Inference
        with predictor.profilers[1]:
            preds = predictor.model(im, augment=predictor.args.augment, visualize=predictor.args.visualize)


        # Postprocess
        with predictor.profilers[2]:
            predictor.results = predictor.postprocess(preds, im, im0s)
        predictor.run_callbacks('on_predict_postprocess_end')
        
        # Visualize, save, write results
        n = len(im0s)
        for i in range(n):
            
            if predictor.dataset.source_type.tensor:  # skip write, show and plot operations if input is raw tensor
                continue
            p, im0 = path[i], im0s[i].copy()
            p = Path(p)
            
            with predictor.profilers[3]:
                # get raw bboxes tensor
                dets = predictor.results[i].boxes.data
                # get tracker predictions
                predictor.tracker_outputs[i] = predictor.trackers[i].update(dets.cpu().detach(), im0)
            predictor.results[i].speed = {
                'preprocess': predictor.profilers[0].dt * 1E3 / n,
                'inference': predictor.profilers[1].dt * 1E3 / n,
                'postprocess': predictor.profilers[2].dt * 1E3 / n,
                'tracking': predictor.profilers[3].dt * 1E3 / n
            }

            if predictor.tracker_outputs[i].size != 0:
                
                # filter boxes masks and pose results by tracking results
                predictor.tracker_outputs[i] = predictor.tracker_outputs[i][predictor.tracker_outputs[i][:, 5].argsort()[::-1]]
                yolo_confs = predictor.results[i].boxes.conf.cpu().numpy()
                tracker_confs = predictor.tracker_outputs[i][:, 5]
                mask = np.in1d(yolo_confs, tracker_confs)
                
                if predictor.results[i].masks is not None:
                    predictor.results[i].masks = predictor.results[i].masks[mask]
                    predictor.results[i].boxes = predictor.results[i].boxes[mask]
                elif predictor.results[i].keypoints is not None:
                    predictor.results[i].boxes = predictor.results[i].boxes[mask]
                    predictor.results[i].keypoints = predictor.results[i].keypoints[mask]
                
                # overwrite bbox results with tracker predictions
                predictor.results[i].boxes = Boxes(
                    # xyxy, (track_id), conf, cls
                    boxes=torch.from_numpy(predictor.tracker_outputs[i]).to(dets.device),
                    orig_shape=im0.shape[:2],  # (height, width)
                )


                candidates, subsets  = [], []
                names = predictor.results[i].names
                for box in predictor.results[i].boxes.cpu().numpy():
                    # if box.conf[0] < predictor.args.people_conf:
                    #     continue
                    # if names[box.cls[0]] != 'person':
                    #     continue
                    # print(box.xyxy)
                    xyxy = [math.floor(i) for i in box.xyxy[0]]
                    mask = np.zeros_like(predictor.results[0].orig_img)
                    mask[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2],:] = 1
                    # cv2.imshow('mask', mask)
                    # cv2.imshow('origimg', predictor.results[i].orig_img)
                    object = predictor.results[i].orig_img*mask
                    # cv2.imshow('object', object)
                    # cv2.waitKey(0)
                    with predictor.profilers[4]:
                        candidate, subset = body_estimation(object)
                    candidates.append(candidate), subsets.append(subset)
                    predictor.results[i].orig_img = util.draw_bodypose(predictor.results[i].orig_img, candidate, subset)
                    # cv2.imshow('img', predictor.results[i].orig_img)
                    # cv2.waitKey(0)
                write_json_results(predictor.save_dir/'labels'/p.stem, predictor.results[i].boxes.cpu().numpy(), frame_idx, candidates, subsets)


                
                #len_boxes = len(predictor.results[i].boxes)
                #predictor.results[i].masks = predictor.results[i].masks[0:len_boxes]
            
            # write inference results to a file or directory   
            if predictor.args.verbose or predictor.args.save or predictor.args.save_txt or predictor.args.show:
                s += predictor.write_results(i, predictor.results, (p, im, im0))
                s += f'person ids: {[str(int(box.id[0])) for box in predictor.results[i].boxes.cpu().numpy()]}, '
                predictor.txt_path = Path(predictor.txt_path)
                
                # write MOT specific results
                if predictor.args.source.endswith(VID_FORMATS):
                    predictor.MOT_txt_path = predictor.txt_path.parent / p.stem
                else:
                    # append folder name containing current img
                    predictor.MOT_txt_path = predictor.txt_path.parent / p.parent.name
                    
                if predictor.tracker_outputs[i].size != 0 and predictor.args.save_txt:
                    write_MOT_results(
                        predictor.MOT_txt_path,
                        predictor.results[i],
                        frame_idx,
                        i,
                    )

            # display an image in a window using OpenCV imshow()
            if predictor.args.show and predictor.plotted_img is not None:
                predictor.show(p.parent)

            # save video predictions
            if predictor.args.save and predictor.plotted_img is not None:
                predictor.save_preds(vid_cap, i, str(predictor.save_dir / p.name))

        predictor.run_callbacks('on_predict_batch_end')

        # print time (inference-only)
        if predictor.args.verbose:
            LOGGER.info(f'{s}YOLO {predictor.profilers[1].dt * 1E3:.1f}ms, TRACKING {predictor.profilers[3].dt * 1E3:.1f}ms, POSE {predictor.profilers[4].dt*1E3:.1f}ms')

    # Release assets
    if isinstance(predictor.vid_writer[-1], cv2.VideoWriter):
        predictor.vid_writer[-1].release()  # release final video writer

    # Print results
    if predictor.args.verbose and predictor.seen:
        t = tuple(x.t / predictor.seen * 1E3 for x in predictor.profilers)  # speeds per image
        LOGGER.info(f'Speed: %.1fms preprocess, %.1fms inference, %.1fms postprocess, %.1fms tracking per image at shape '
                    f'{(1, 3, *predictor.args.imgsz)}' % t)
    if predictor.args.save or predictor.args.save_txt or predictor.args.save_crop:
        nl = len(list(predictor.save_dir.glob('labels/*.txt')))  # number of labels
        s = f"\n{nl} label{'s' * (nl > 1)} saved to {predictor.save_dir / 'labels'}" if predictor.args.save_txt else ''
        LOGGER.info(f"Results saved to {colorstr('bold', predictor.save_dir)}{s}")

    predictor.run_callbacks('on_predict_end')
    

def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--yolo-model', type=str, default=WEIGHTS / 'yolov8n.pt', help='model.pt path(s)')
    parser.add_argument('--reid-model', type=Path, default=WEIGHTS / 'mobilenetv2_x1_4_dukemtmcreid.pt')
    parser.add_argument('--tracking-method', type=str, default='deepocsort', help='deepocsort, botsort, strongsort, ocsort, bytetrack')
    parser.add_argument('--source', type=str, default='0', help='file/dir/URL/glob, 0 for webcam')  
    parser.add_argument('--imgsz', '--img', '--img-size', nargs='+', type=int, default=[640], help='inference size h,w')
    parser.add_argument('--conf', type=float, default=0.5, help='confidence threshold')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--show', action='store_true', help='display tracking video results')
    parser.add_argument('--save', action='store_true', help='save video tracking results')
    # # class 0 is person, 1 is bycicle, 2 is car... 79 is oven
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --classes 0, or --classes 0 2 3')
    parser.add_argument('--project', default=ROOT / 'runs' / 'track', help='save results to project/name')
    parser.add_argument('--name', default='exp', help='save results to project/name')
    parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
    parser.add_argument('--half', action='store_true', help='use FP16 half-precision inference')
    parser.add_argument('--vid-stride', type=int, default=1, help='video frame-rate stride')
    parser.add_argument('--hide-label', action='store_true', help='hide labels when show')
    parser.add_argument('--hide-conf', action='store_true', help='hide confidences when show')
    parser.add_argument('--save-txt', action='store_true', help='save tracking results in a txt file')
    opt = parser.parse_args()
    print_args(vars(opt))
    return opt


def main(opt):
    opt = vars(opt)
    opt['yolo_model'] = WEIGHTS / 'yolov8n.pt'
    opt['reid_model'] = WEIGHTS / 'mobilenetv2_x1_4_dukemtmcreid.pt'
    opt['tracking_method'] = 'deepocsort'
    opt['source'] = '0'
    opt['source'] = '../video/lwf_running_f_right_1.MP4'
    opt['people_conf'] = 0.7
    # opt['device'] = 0
    opt['classes'] = 0
    opt['conf'] = 0.7
    opt['show'] = True
    opt['save'] = True
    opt['save_txt'] = True
    opt['save_json'] = True
    run(opt)


if __name__ == "__main__":
    opt = parse_opt()
    main(opt)