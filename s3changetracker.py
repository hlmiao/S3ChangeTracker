import boto3
from datetime import datetime

CONFIG = {
    "TARGET_BUCKET": "leiwo-nasa",              # 要扫描的S3桶
    "STATE_BUCKET": "leiwo-results",            # 状态文件和结果文件的S3桶
    "STATE_KEY": "status/s3_scan_state.txt",    # 状态文件路径 
    "TARGET_PREFIX": "tiles/45/R/VL/2025/",     # 扫描路径前缀
    "RESULT_PREFIX": "results/"                 # 扫描结果存放路径
}

s3 = boto3.client('s3')

def get_s3_objects(prefix):
    """递归获取所有对象"""
    paginator = s3.get_paginator('list_objects_v2')
    files = {}
    for page in paginator.paginate(
        Bucket=CONFIG['TARGET_BUCKET'],
        Prefix=prefix,
        Delimiter='/'
    ):
        # 处理文件
        if 'Contents' in page:
            for obj in page['Contents']:
                if not obj['Key'].endswith('/'):
                    files[obj['Key']] = {
                        'ETag': obj['ETag'].strip('"'),
                        'LastModified': obj['LastModified'].timestamp()
                    }
        # 递归子目录
        if 'CommonPrefixes' in page:
            for subdir in page['CommonPrefixes']:
                files.update(get_s3_objects(subdir['Prefix']))
    return files

def load_previous_state():
    """加载状态文件,增强错误处理"""
    try:
        response = s3.get_object(
            Bucket=CONFIG['STATE_BUCKET'],
            Key=CONFIG['STATE_KEY']
        )
        return {
            line.split(',')[0]: {
                'ETag': line.split(',')[1],
                'LastModified': float(line.split(',')[2])
            }
            for line in response['Body'].read().decode('utf-8').splitlines()
        }
    except s3.exceptions.NoSuchKey:
        print("首次运行，状态文件不存在")
        return {}
    except Exception as e:
        print(f"加载状态文件失败: {str(e)}")
        return {}

def save_current_state(current_state):
    """保存状态文件,强制覆盖"""
    s3.put_object(
        Bucket=CONFIG['STATE_BUCKET'],
        Key=CONFIG['STATE_KEY'],
        Body='\n'.join([
            f"{k},{v['ETag']},{v['LastModified']}"
            for k, v in current_state.items()
        ]).encode('utf-8')
    )

def save_scan_result(new_files, modified_files):
    """保存结果文件,带时间戳"""
    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    result_key = f"{CONFIG['RESULT_PREFIX']}scan_{now}.txt"
    content = f"Scan Time: {now}\n\nNew Files ({len(new_files)}):\n" + '\n'.join(new_files) + \
              f"\n\nModified Files ({len(modified_files)}):\n" + '\n'.join(modified_files)
    s3.put_object(
        Bucket=CONFIG['STATE_BUCKET'],
        Key=result_key,
        Body=content.encode('utf-8')
    )
    return result_key

def lambda_handler(event, context):
    try:
        # 打印调试信息
        print(f"开始扫描: s3://{CONFIG['TARGET_BUCKET']}/{CONFIG['TARGET_PREFIX']}")
        
        previous_state = load_previous_state()
        current_state = get_s3_objects(CONFIG['TARGET_PREFIX'])
        
        print(f"扫描到对象数量: {len(current_state)}")
        print(f"上次状态记录数量: {len(previous_state)}")
        
        new_files = [k for k in current_state if k not in previous_state]
        modified_files = [
            k for k in current_state
            if k in previous_state and (
                current_state[k]['ETag'] != previous_state[k]['ETag'] or
                current_state[k]['LastModified'] > previous_state[k]['LastModified']
            )
        ]
        
        print(f"新增文件: {len(new_files)}, 修改文件: {len(modified_files)}")
        
        save_current_state(current_state)
        result_key = save_scan_result(new_files, modified_files)
        
        return {
            "status": "SUCCESS",
            "result_file": f"s3://{CONFIG['STATE_BUCKET']}/{result_key}"
        }
    except Exception as e:
        print(f"错误: {str(e)}")
        return {
            "status": "FAILED",
            "error": str(e)
        }
