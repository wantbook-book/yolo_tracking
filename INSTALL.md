## 跟踪姿态识别

结合了https://github.com/Hzzone/pytorch-openpose（进行姿态识别）和https://github.com/mikel-brostrom/yolo_tracking（进行识别跟踪）

## 环境配置

1. 使用python3.10环境

2. 安装依赖

   ```bash
   # yolo_tracking requirements
   pip install boxmot
   pip install -r requirements.txt
   # pytorch-openpose requirements
   pip install -r examples/pytorch_openpose/requirements.txt
   ```

3. 模型下载

   `yolo_tracking/examples/pytorch_openpose/model/body_pose_model.pth`和`/home/disk3/fwk/yolo_tracking/examples/pytorch_openpose/model/hand_pose_model.pth`下载：

   - [dropbox](https://www.dropbox.com/sh/7xbup2qsn7vvjxo/AABWFksdlgOMXR_r5v3RwKRYa?dl=0)
   - [baiduyun](https://pan.baidu.com/s/1IlkvuSi0ocNckwbnUe7j-g)
   - [google drive](https://drive.google.com/drive/folders/1JsvI4M4ZTg98fmnCZLFM-3TeovnCRElG?usp=sharing)

   `yolo_tracking/examples/weights/mobilenetv2_x1_4_dukemtmcreid.pt`和`yolo_tracking/examples/weights/yolov8n.pt`会自动下载

   

4. 

## 运行参数

可在`examples/track.py`的`main()`函数中修改`opt`变量修改参数。

1. `show`: 有gui界面可以显示图片结果

2. `save_json`：输出识别跟踪、姿态识别结果

   将输出到`runs/track/exp/labels/*.json`

   json结构如下：

   ```json
   [
       {
           "frame_idx": 0,
           "people": [
               {
                   "id": 1,
                   "xyxy": [
                       130.38580322265625,
                       456.4355163574219,
                       326.11151123046875,
                       1074.0827331542969
                   ],
                   "pose_points": [
                       [
                           237.0,
                           525.0
                       ],
                       [
                           234.0,
                           597.0
                       ],
                       [
                           179.0,
                           598.0
                       ],
                       [
                           158.0,
                           696.0
                       ],
                       [
                           154.0,
                           776.0
                       ],
                       [
                           291.0,
                           595.0
                       ],
                       [
                           309.0,
                           686.0
                       ],
                       [
                           307.0,
                           760.0
                       ],
                       [
                           196.0,
                           775.0
                       ],
                       [
                           187.0,
                           903.0
                       ],
                       [
                           177.0,
                           1029.0
                       ],
                       [
                           266.0,
                           775.0
                       ],
                       [
                           264.0,
                           902.0
                       ],
                       [
                           255.0,
                           1029.0
                       ],
                       [
                           220.0,
                           516.0
                       ],
                       [
                           248.0,
                           515.0
                       ],
                       [
                           200.0,
                           524.0
                       ],
                       [
                           260.0,
                           522.0
                       ]
                   ]
               },
               {
                   "id": 2,
                   "xyxy": [
                       363.8314208984375,
                       411.972412109375,
                       607.53173828125,
                       1157.9779052734375
                   ],
                   "pose_points": [
                       [
                           445.0,
                           479.0
                       ],
                       [
                           485.0,
                           574.0
                       ],
                       [
                           425.0,
                           573.0
                       ],
                       [
                           401.0,
                           685.0
                       ],
                       [
                           401.0,
                           782.0
                       ],
                       [
                           550.0,
                           576.0
                       ],
                       [
                           576.0,
                           691.0
                       ],
                       [
                           573.0,
                           792.0
                       ],
                       [
                           441.0,
                           800.0
                       ],
                       [
                           417.0,
                           931.0
                       ],
                       [
                           410.0,
                           1071.0
                       ],
                       [
                           523.0,
                           804.0
                       ],
                       [
                           516.0,
                           947.0
                       ],
                       [
                           513.0,
                           1086.0
                       ],
                       [
                           439.0,
                           471.0
                       ],
                       [
                           464.0,
                           469.0
                       ],
                       [
                           0,
                           0
                       ],
                       [
                           501.0,
                           475.0
                       ]
                   ]
               }
           ]
       },
       {
           "frame_idx": 1,
           "people": [
               {
                   "id": 1,
                   "xyxy": [
                       130.40679931640625,
                       456.52001953125,
                       326.3775634765625,
                       1074.244140625
                   ],
                   "pose_points": [
                       [
                           237.0,
                           525.0
                       ],
                       [
                           234.0,
                           597.0
                       ],
                       [
                           178.0,
                           598.0
                       ],
                       [
                           158.0,
                           696.0
                       ],
                       [
                           154.0,
                           776.0
                       ],
                       [
                           291.0,
                           595.0
                       ],
                       [
                           309.0,
                           686.0
                       ],
                       [
                           307.0,
                           760.0
                       ],
                       [
                           196.0,
                           775.0
                       ],
                       [
                           187.0,
                           902.0
                       ],
                       [
                           178.0,
                           1028.0
                       ],
                       [
                           267.0,
                           775.0
                       ],
                       [
                           263.0,
                           904.0
                       ],
                       [
                           255.0,
                           1030.0
                       ],
                       [
                           220.0,
                           516.0
                       ],
                       [
                           248.0,
                           514.0
                       ],
                       [
                           200.0,
                           524.0
                       ],
                       [
                           260.0,
                           522.0
                       ]
                   ]
               },
               {
                   "id": 2,
                   "xyxy": [
                       364.993408203125,
                       412.018310546875,
                       607.5508422851562,
                       1157.7933349609375
                   ],
                   "pose_points": [
                       [
                           446.0,
                           482.0
                       ],
                       [
                           485.0,
                           576.0
                       ],
                       [
                           424.0,
                           574.0
                       ],
                       [
                           401.0,
                           686.0
                       ],
                       [
                           403.0,
                           783.0
                       ],
                       [
                           550.0,
                           578.0
                       ],
                       [
                           576.0,
                           693.0
                       ],
                       [
                           573.0,
                           793.0
                       ],
                       [
                           442.0,
                           801.0
                       ],
                       [
                           417.0,
                           932.0
                       ],
                       [
                           409.0,
                           1073.0
                       ],
                       [
                           523.0,
                           805.0
                       ],
                       [
                           517.0,
                           949.0
                       ],
                       [
                           515.0,
                           1087.0
                       ],
                       [
                           438.0,
                           473.0
                       ],
                       [
                           465.0,
                           471.0
                       ],
                       [
                           0,
                           0
                       ],
                       [
                           503.0,
                           477.0
                       ]
                   ]
               }
           ]
       }
   ]
   ```
3. source：0为启用摄像头，可视频路径