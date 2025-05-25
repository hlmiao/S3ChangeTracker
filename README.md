## 1.资源准备
在部署和运行代码前，请提前准备以下 AWS 资源：

### 源数据 S3 桶
存放需要监控的对象（如遥感图片等）。  
例如：`leiwo-nasa`

### 结果 S3 桶
用于存放状态文件和扫描结果文件。建议与源桶分离，便于权限管理。  
例如：`leiwo-results`

### S3 路径前缀
希望扫描的对象前缀（如：`tiles/45/R/VL/2025/`）

### Lambda 执行角色
需要有如下权限（以 JSON Policy 片段为例）：
{
###### "Effect": "Allow",
###### "Action": [
###### "s3:ListBucket",
###### "s3:GetObject",
###### "s3:PutObject"
###### ],
###### "Resource": [
###### "arn:aws:s3:::leiwo-nasa",
###### "arn:aws:s3:::leiwo-nasa/",
###### "arn:aws:s3:::leiwo-results",
###### "arn:aws:s3:::leiwo-results/"
###### ]
###### }

## 2.主要功能

- **全量扫描**  
  首次运行时，扫描指定前缀下所有对象，生成状态文件。

- **增量检测**  
  后续运行时，仅记录新增和有变化（内容或修改时间不同）的对象。

- **状态文件**  
  以 txt 格式存储，每行一个对象的路径、ETag 和修改时间。

- **变更结果文件**  
  每次扫描结果以 txt 文件保存，包含扫描时间、新增对象和变化对象列表。

## 3.目录结构示例
##### leiwo-results/status/s3_scan_state.txt        # 状态文件（每行：key,etag,last_modified）
##### leiwo-results/results/scan_20250525_153000.txt # 扫描结果文件（txt）
