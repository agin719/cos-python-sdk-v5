# -*- coding=utf-8
import random
import sys
import time
import hashlib
import os
import requests
import json
from qcloud_cos import CosS3Client
from qcloud_cos import CosConfig
from qcloud_cos import CosServiceError
from qcloud_cos import get_date

SECRET_ID = os.environ["SECRET_ID"]
SECRET_KEY = os.environ["SECRET_KEY"]
TRAVIS_FLAG = os.environ["TRAVIS_FLAG"]
REGION = os.environ["REGION"]
APPID = '1251668577'
test_bucket = 'cos-python-v5-test-' + str(sys.version_info[0]) + '-' + str(sys.version_info[1]) + '-' + REGION + '-' + APPID
test_object = "test.txt"
special_file_name = "中文" + "→↓←→↖↗↙↘! \"#$%&'()*+,-./0123456789:;<=>@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
conf = CosConfig(
    Region=REGION,
    SecretId=SECRET_ID,
    SecretKey=SECRET_KEY,
)
client = CosS3Client(conf, retry=3)


def _create_test_bucket(test_bucket):
    try:
        response = client.create_bucket(
            Bucket=test_bucket,
        )
    except Exception as e:
        if e.get_error_code() == 'BucketAlreadyOwnedByYou':
            print('BucketAlreadyOwnedByYou')
        else:
            raise e
    return None


def get_raw_md5(data):
    m2 = hashlib.md5(data)
    etag = '"' + str(m2.hexdigest()) + '"'
    return etag


def gen_file(path, size):
    _file = open(path, 'w')
    _file.seek(1024*1024*size-3)
    _file.write('cos')
    _file.close()


def print_error_msg(e):
    print (e.get_origin_msg())
    print (e.get_digest_msg())
    print (e.get_status_code())
    print (e.get_error_code())
    print (e.get_error_msg())
    print (e.get_resource_location())
    print (e.get_trace_id())
    print (e.get_request_id())


def setUp():
    print ("start test...")
    print ("start create bucket " + test_bucket)
    _create_test_bucket(test_bucket)


def tearDown():
    print ("function teardown")


def test_put_get_delete_object_10MB():
    """简单上传下载删除10MB小文件"""
    file_size = 10
    file_id = str(random.randint(0, 1000)) + str(random.randint(0, 1000))
    file_name = "tmp" + file_id + "_" + str(file_size) + "MB"
    gen_file(file_name, 1)
    with open(file_name, 'rb') as f:
        etag = get_raw_md5(f.read())
    try:
        # put object
        with open(file_name, 'rb') as fp:
            put_response = client.put_object(
                Bucket=test_bucket,
                Body=fp,
                Key=file_name,
                CacheControl='no-cache',
                ContentDisposition='download.txt'
            )
        assert etag == put_response['ETag']
        # head object
        head_response = client.head_object(
            Bucket=test_bucket,
            Key=file_name
        )
        assert etag == head_response['ETag']
        # get object
        get_response = client.get_object(
            Bucket=test_bucket,
            Key=file_name,
            ResponseCacheControl='private'
        )
        assert etag == get_response['ETag']
        assert 'private' == get_response['Cache-Control']
        download_fp = get_response['Body'].get_raw_stream()
        assert download_fp
        # delete object
        delete_response = client.delete_object(
            Bucket=test_bucket,
            Key=file_name
        )
    except CosServiceError as e:
        print_error_msg(e)
    if os.path.exists(file_name):
        os.remove(file_name)


def test_put_object_speacil_names():
    """特殊字符文件上传"""
    response = client.put_object(
        Bucket=test_bucket,
        Body='S'*1024,
        Key=special_file_name,
        CacheControl='no-cache',
        ContentDisposition='download.txt'
    )
    assert response


def test_get_object_special_names():
    """特殊字符文件下载"""
    response = client.get_object(
        Bucket=test_bucket,
        Key=special_file_name
    )
    assert response


def test_delete_object_special_names():
    """特殊字符文件删除"""
    response = client.delete_object(
        Bucket=test_bucket,
        Key=special_file_name
    )


def test_put_object_non_exist_bucket():
    """文件上传至不存在bucket"""
    try:
        response = client.put_object(
            Bucket='test0xx-' + APPID,
            Body='T'*10,
            Key=test_object,
            CacheControl='no-cache',
            ContentDisposition='download.txt'
        )
    except CosServiceError as e:
        print_error_msg(e)


def test_put_object_acl():
    """设置object acl"""
    response = client.put_object(
        Bucket=test_bucket,
        Key=test_object,
        Body='test acl'
    )
    response = client.put_object_acl(
        Bucket=test_bucket,
        Key=test_object,
        ACL='public-read'
    )


def test_get_object_acl():
    """获取object acl"""
    response = client.get_object_acl(
        Bucket=test_bucket,
        Key=test_object
    )
    assert response
    response = client.delete_object(
        Bucket=test_bucket,
        Key=test_object
    )


def test_copy_object_diff_bucket():
    """从另外的bucket拷贝object"""
    copy_source = {'Bucket': 'test04-' + APPID, 'Key': '/test.txt', 'Region': 'ap-guangzhou'}
    response = client.copy_object(
        Bucket=test_bucket,
        Key='test.txt',
        CopySource=copy_source
    )
    assert response


def test_create_abort_multipart_upload():
    """创建一个分块上传，然后终止它"""
    # create
    response = client.create_multipart_upload(
        Bucket=test_bucket,
        Key='multipartfile.txt',
    )
    assert response
    uploadid = response['UploadId']
    # abort
    response = client.abort_multipart_upload(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid
    )


def test_create_complete_multipart_upload():
    """创建一个分块上传，上传分块，列出分块，完成分块上传"""
    # create
    response = client.create_multipart_upload(
        Bucket=test_bucket,
        Key='multipartfile.txt',
    )
    uploadid = response['UploadId']
    # upload part
    response = client.upload_part(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid,
        PartNumber=1,
        Body='A'*1024*1024*2
    )

    response = client.upload_part(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid,
        PartNumber=2,
        Body='B'*1024*1024*2
    )
    # list parts
    response = client.list_parts(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid
    )
    lst = response['Part']
    # complete
    response = client.complete_multipart_upload(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid,
        MultipartUpload={'Part': lst}
    )


def test_upload_part_copy():
    """创建一个分块上传，上传分块拷贝，列出分块，完成分块上传"""
    # create
    response = client.create_multipart_upload(
        Bucket=test_bucket,
        Key='multipartfile.txt',
    )
    uploadid = response['UploadId']
    # upload part
    response = client.upload_part(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid,
        PartNumber=1,
        Body='A'*1024*1024*2
    )

    response = client.upload_part(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid,
        PartNumber=2,
        Body='B'*1024*1024*2
    )

    # upload part copy
    copy_source = {'Bucket': 'test04-' + APPID, 'Key': '/test.txt', 'Region': 'ap-guangzhou'}
    response = client.upload_part_copy(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid,
        PartNumber=3,
        CopySource=copy_source
    )
    # list parts
    response = client.list_parts(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid
    )
    lst = response['Part']
    # complete
    response = client.complete_multipart_upload(
        Bucket=test_bucket,
        Key='multipartfile.txt',
        UploadId=uploadid,
        MultipartUpload={'Part': lst}
    )


def test_delete_multiple_objects():
    """批量删除文件"""
    file_id = str(random.randint(0, 1000)) + str(random.randint(0, 1000))
    file_name1 = "tmp" + file_id + "_delete1"
    file_name2 = "tmp" + file_id + "_delete2"
    response1 = client.put_object(
        Bucket=test_bucket,
        Key=file_name1,
        Body='A'*1024*1024
    )
    assert response1
    response2 = client.put_object(
        Bucket=test_bucket,
        Key=file_name2,
        Body='B'*1024*1024*2
    )
    assert response2
    objects = {
        "Quiet": "true",
        "Object": [
            {
                "Key": file_name1
            },
            {
                "Key": file_name2
            }
        ]
    }
    response = client.delete_objects(
        Bucket=test_bucket,
        Delete=objects
    )


def test_create_head_delete_bucket():
    """创建一个bucket,head它是否存在,最后删除一个空bucket"""
    bucket_id = str(random.randint(0, 1000)) + str(random.randint(0, 1000))
    bucket_name = 'buckettest' + bucket_id + '-' + APPID
    response = client.create_bucket(
        Bucket=bucket_name,
        ACL='public-read'
    )
    response = client.head_bucket(
        Bucket=bucket_name
    )
    response = client.delete_bucket(
        Bucket=bucket_name
    )


def test_put_bucket_acl_illegal():
    """设置非法的ACL"""
    try:
        response = client.put_bucket_acl(
            Bucket=test_bucket,
            ACL='public-read-writ'
        )
    except CosServiceError as e:
        print_error_msg(e)


def test_get_bucket_acl_normal():
    """正常获取bucket ACL"""
    response = client.get_bucket_acl(
        Bucket=test_bucket
    )
    assert response


def test_list_objects():
    """列出bucket下的objects"""
    response = client.list_objects(
        Bucket=test_bucket,
        MaxKeys=100,
        Prefix='中文',
        Delimiter='/'
    )
    assert response


def test_list_objects_versions():
    """列出bucket下的带版本信息的objects"""
    response = client.list_objects_versions(
        Bucket=test_bucket,
        MaxKeys=50
    )
    assert response


def test_get_presigned_url():
    """生成预签名的url下载地址"""
    url = client.get_presigned_download_url(
        Bucket=test_bucket,
        Key='中文.txt'
    )
    assert url
    print (url)


def test_get_bucket_location():
    """获取bucket的地域信息"""
    response = client.get_bucket_location(
        Bucket=test_bucket
    )
    assert response['LocationConstraint'] == REGION


def test_get_service():
    """列出账号下所有的bucket信息"""
    response = client.list_buckets()
    assert response


def test_put_get_delete_cors():
    """设置、获取、删除跨域配置"""
    cors_config = {
        'CORSRule': [
            {
                'ID': '1234',
                'AllowedOrigin': ['http://www.qq.com'],
                'AllowedMethod': ['GET', 'PUT'],
                'AllowedHeader': ['x-cos-meta-test'],
                'ExposeHeader': ['x-cos-meta-test1'],
                'MaxAgeSeconds': 500
            }
         ]
    }
    # put cors
    response = client.put_bucket_cors(
        Bucket=test_bucket,
        CORSConfiguration=cors_config
    )
    # wait for sync
    # get cors
    time.sleep(4)
    response = client.get_bucket_cors(
        Bucket=test_bucket
    )
    assert response
    # delete cors
    response = client.get_bucket_cors(
        Bucket=test_bucket
    )


def test_put_get_delete_lifecycle():
    """设置、获取、删除生命周期配置"""
    lifecycle_config = {
        'Rule': [
            {
                'Status': 'Enabled',
                'Filter': {
                    # 作用于带标签键 datalevel 和值 backup 的标签的对象
                    'Tag': [
                        {
                            'Key': 'datalevel',
                            'Value': 'backup'
                        }
                    ]
                },
                'Transation': [
                    {
                        # 30天后转换为Standard_IA
                        'Days': 30,
                        'StorageClass': 'Standard_IA'
                    }
                ],
                'Expiration': {
                    # 3650天后过期删除
                    'Days': 3650
                }
            }
        ]
    }
    try:
        # put lifecycle
        response = client.put_bucket_lifecycle(
            Bucket=test_bucket,
            LifecycleConfiguration=lifecycle_config
        )
        # wait for sync
        # get lifecycle
        time.sleep(4)
        response = client.get_bucket_lifecycle(
            Bucket=test_bucket
        )
        assert response
        # delete lifecycle
        response = client.delete_bucket_lifecycle(
            Bucket=test_bucket
        )
    except CosServiceError as e:
        if e.get_status_code() < 500:
            raise e


def test_put_get_versioning():
    """设置、获取版本控制"""
    # put versioning
    response = client.put_bucket_versioning(
        Bucket=test_bucket,
        Status='Enabled'
    )
    # wait for sync
    # get versioning
    time.sleep(4)
    response = client.get_bucket_versioning(
        Bucket=test_bucket
    )
    assert response['Status'] == 'Enabled'


def test_put_get_delete_replication():
    """设置、获取、删除跨园区复制配置"""
    replication_config = {
        'Role': 'qcs::cam::uin/2779643970:uin/2779643970',
        'Rule': [
            {
                'ID': '123',
                'Status': 'Enabled',
                'Prefix': '中文',
                'Destination': {
                    'Bucket': 'qcs:id/0:cos:ap-shanghai:appid/1251668577:replicationsh'
                }
            }
        ]
    }
    # source dest bucket must enable versioning
    # put replication
    response = client.put_bucket_replication(
        Bucket=test_bucket,
        ReplicationConfiguration=replication_config
    )
    # wait for sync
    # get replication
    time.sleep(4)
    response = client.get_bucket_replication(
        Bucket=test_bucket
    )
    assert response
    # delete replication
    response = client.delete_bucket_replication(
        Bucket=test_bucket
    )


def test_put_get_delete_website():
    """设置、获取、删除静态网站配置"""
    website_config = {
        'IndexDocument': {
            'Suffix': 'index.html'
        },
        'ErrorDocument': {
            'Key': 'error.html'
        },
        'RoutingRules': [
            {
                'Condition': {
                    'HttpErrorCodeReturnedEquals': '404',
                },
                'Redirect': {
                    'ReplaceKeyWith': '404.html',
                }
            },
            {
                'Condition': {
                    'KeyPrefixEquals': 'aaa/'
                },
                'Redirect': {
                    'ReplaceKeyPrefixWith': 'ccc/'
                }
             }
        ]
    }
    response = client.put_bucket_website(
        Bucket=test_bucket,
        WebsiteConfiguration=website_config
    )
    # wait for sync
    # get website
    time.sleep(4)
    response = client.get_bucket_website(
        Bucket=test_bucket
    )
    assert website_config == response
    # delete website
    response = client.delete_bucket_website(
        Bucket=test_bucket
    )


def test_list_multipart_uploads():
    """获取所有正在进行的分块上传"""
    response = client.list_multipart_uploads(
        Bucket=test_bucket,
        Prefix="multipart",
        MaxUploads=100
    )
    # abort make sure delete all uploads
    if 'Upload' in response.keys():
        for data in response['Upload']:
            response = client.abort_multipart_upload(
                Bucket=test_bucket,
                Key=data['Key'],
                UploadId=data['UploadId']
            )
    # create a new upload
    response = client.create_multipart_upload(
        Bucket=test_bucket,
        Key='multipartfile.txt',
    )
    assert response
    uploadid = response['UploadId']
    # list again
    response = client.list_multipart_uploads(
        Bucket=test_bucket,
        Prefix="multipart",
        MaxUploads=100
    )
    assert response['Upload'][0]['Key'] == "multipartfile.txt"
    assert response['Upload'][0]['UploadId'] == uploadid
    # abort again make sure delete all uploads
    for data in response['Upload']:
        response = client.abort_multipart_upload(
            Bucket=test_bucket,
            Key=data['Key'],
            UploadId=data['UploadId']
        )


def test_upload_file_from_buffer():
    import io
    data = io.BytesIO(6*1024*1024*b'A')
    response = client.upload_file_from_buffer(
        Bucket=test_bucket,
        Key='test_upload_from_buffer',
        Body=data,
        MaxBufferSize=5,
        PartSize=1
    )


def test_upload_file_multithreading():
    """根据文件大小自动选择分块大小,多线程并发上传提高上传速度"""
    file_name = "thread_1GB"
    file_size = 1024
    if TRAVIS_FLAG == 'true':
        file_size = 5  # set 5MB beacuse travis too slow
    gen_file(file_name, file_size)
    st = time.time()  # 记录开始时间
    response = client.upload_file(
        Bucket=test_bucket,
        Key=file_name,
        LocalFilePath=file_name,
        MAXThread=5,
        EnableMD5=True
    )
    ed = time.time()  # 记录结束时间
    if os.path.exists(file_name):
        os.remove(file_name)
    print (ed - st)


def test_copy_file_automatically():
    """根据拷贝源文件的大小自动选择拷贝策略，不同园区,小于5G直接copy_object，大于5G分块拷贝"""
    copy_source = {'Bucket': 'test01-' + APPID, 'Key': '/thread_1MB', 'Region': 'ap-guangzhou'}
    response = client.copy(
        Bucket=test_bucket,
        Key='copy_10G.txt',
        CopySource=copy_source,
        MAXThread=10
    )


def test_upload_empty_file():
    """上传一个空文件,不能返回411错误"""
    file_name = "empty.txt"
    with open(file_name, 'wb') as f:
        pass
    with open(file_name, 'rb') as fp:
        response = client.put_object(
            Bucket=test_bucket,
            Body=fp,
            Key=file_name,
            CacheControl='no-cache',
            ContentDisposition='download.txt'
        )


def test_copy_10G_file_in_same_region():
    """同园区的拷贝,应该直接用copy_object接口,可以直接秒传"""
    copy_source = {'Bucket': 'test01-' + APPID, 'Key': '10G.txt', 'Region': 'ap-guangzhou'}
    copy_config = CosConfig(Region='ap-guangzhou', SecretId=SECRET_ID, SecretKey=SECRET_KEY)
    copy_client = CosS3Client(copy_config)
    response = copy_client.copy(
        Bucket='test04-' + APPID,
        Key='10G.txt',
        CopySource=copy_source,
        MAXThread=10
    )


def test_use_get_auth():
    """测试利用get_auth方法直接生产签名,然后访问COS"""
    auth = client.get_auth(
        Method='GET',
        Bucket=test_bucket,
        Key='test.txt',
        Params={'acl': '', 'unsed': '123'}
    )
    url = 'http://' + test_bucket + '.cos.' + REGION + '.myqcloud.com/test.txt?acl&unsed=123'
    response = requests.get(url, headers={'Authorization': auth})
    assert response.status_code == 200


def test_upload_with_server_side_encryption():
    """上传带上加密头部,下载时验证有该头部"""
    response = client.put_object(
        Bucket=test_bucket,
        Key=test_object,
        Body='123',
        ServerSideEncryption='AES256'
    )
    assert response['x-cos-server-side-encryption'] == 'AES256'


def test_put_get_bucket_logging():
    """测试bucket的logging服务"""
    logging_bucket = 'logging-beijing-' + APPID
    logging_config = {
        'LoggingEnabled': {
            'TargetBucket': logging_bucket,
            'TargetPrefix': 'test'
        }
    }
    beijing_conf = CosConfig(
        Region="ap-beijing",
        Secret_id=SECRET_ID,
        Secret_key=SECRET_KEY
    )
    logging_client = CosS3Client(beijing_conf)
    response = logging_client.put_bucket_logging(
        Bucket=logging_bucket,
        BucketLoggingStatus=logging_config
    )
    time.sleep(4)
    response = logging_client.get_bucket_logging(
        Bucket=logging_bucket
    )
    print (response)
    assert response['LoggingEnabled']['TargetBucket'] == logging_bucket
    assert response['LoggingEnabled']['TargetPrefix'] == 'test'


def test_put_object_enable_md5():
    """上传文件,SDK计算content-md5头部"""
    file_name = 'test_object_sdk_caculate_md5.file'
    gen_file(file_name, 1)
    with open(file_name, 'rb') as f:
        etag = get_raw_md5(f.read())
    with open(file_name, 'rb') as fp:
        # fp验证
        put_response = client.put_object(
            Bucket=test_bucket,
            Body=fp,
            Key=file_name,
            EnableMD5=True,
            CacheControl='no-cache',
            ContentDisposition='download.txt'
        )
        assert etag == put_response['ETag']
        put_response = client.put_object(
            Bucket=test_bucket,
            Body='TestMD5',
            Key=file_name,
            EnableMD5=True,
            CacheControl='no-cache',
            ContentDisposition='download.txt'
        )
        assert put_response
    if os.path.exists(file_name):
        os.remove(file_name)


def test_put_object_from_local_file():
    """通过本地文件路径来上传文件"""
    file_size = 1
    file_id = str(random.randint(0, 1000)) + str(random.randint(0, 1000))
    file_name = "tmp" + file_id + "_" + str(file_size) + "MB"
    gen_file(file_name, file_size)
    with open(file_name, 'rb') as f:
        etag = get_raw_md5(f.read())
    put_response = client.put_object_from_local_file(
        Bucket=test_bucket,
        LocalFilePath=file_name,
        Key=file_name
    )
    assert put_response['ETag'] == etag
    response = client.delete_object(
        Bucket=test_bucket,
        Key=file_name
    )
    if os.path.exists(file_name):
        os.remove(file_name)


def test_object_exists():
    """测试一个文件是否存在"""
    status = client.object_exists(
        Bucket=test_bucket,
        Key=test_object
    )
    assert status is True


def test_bucket_exists():
    """测试一个bucket是否存在"""
    status = client.bucket_exists(
        Bucket=test_bucket
    )
    assert status is True


def test_put_get_bucket_policy():
    """设置获取bucket的policy配置"""
    resource = "qcs::cos:" + REGION + ":uid/" + APPID + ":" + test_bucket + "/*"
    resource_list = [resource]
    policy = {
        "Statement": [
            {
                "Principal": {
                    "qcs": [
                        "qcs::cam::anyone:anyone"
                    ]
                },
                "Action": [
                    "name/cos:GetObject",
                    "name/cos:HeadObject"
                ],
                "Effect": "allow",
                "Resource": resource_list
            }
        ],
        "Version": "2.0"
    }
    response = client.put_bucket_policy(
        Bucket=test_bucket,
        Policy=policy
    )
    response = client.get_bucket_policy(
        Bucket=test_bucket,
    )


def test_put_file_like_object():
    """利用BytesIo来模拟文件上传"""
    import io
    input = io.BytesIO(b"123456")
    rt = client.put_object(
        Bucket=test_bucket,
        Key='test_file_like_object',
        Body=input,
        EnableMD5=True
    )
    assert rt


def test_put_chunked_object():
    """支持网络流来支持chunk上传"""
    import requests
    input = requests.get(client.get_presigned_download_url(test_bucket, test_object))
    rt = client.put_object(
        Bucket=test_bucket,
        Key='test_chunked_object',
        Body=input
    )
    assert rt


def test_put_get_gzip_file():
    """上传文件时,带上ContentEncoding,下载时默认不解压"""
    rt = client.put_object(
        Bucket=test_bucket,
        Key='test_gzip_file',
        Body='123456',
        ContentEncoding='gzip',
    )
    rt = client.get_object(
        Bucket=test_bucket,
        Key='test_gzip_file'
    )
    rt['Body'].get_stream_to_file('test_gzip_file.local')


def test_put_get_delete_bucket_domain():
    """测试设置获取删除bucket自定义域名"""
    domain_config = {
        'DomainRule': [
            {
                'Name': 'qq.com',
                'Type': 'REST',
                'Status': 'ENABLED',
            },
        ]
    }
    response = client.put_bucket_domain(
        Bucket=test_bucket,
        DomainConfiguration=domain_config
    )
    # wait for sync
    # get domain
    time.sleep(4)
    response = client.get_bucket_domain(
        Bucket=test_bucket
    )
    domain_config['x-cos-domain-txt-verification'] = response['x-cos-domain-txt-verification']
    assert domain_config == response
    # delete domain
    response = client.delete_bucket_domain(
        Bucket=test_bucket
    )


def test_put_get_delete_bucket_inventory():
    """测试设置获取删除bucket清单"""
    inventory_config = {
        'Destination': {
            'COSBucketDestination': {
                'AccountId': '2779643970',
                'Bucket': 'qcs::cos:' + REGION + '::' + test_bucket,
                'Format': 'CSV',
                'Prefix': 'list1',
                'Encryption': {
                    'SSECOS': {}
                }
            }
        },
        'IsEnabled': 'True',
        'Filter': {
            'Prefix': 'filterPrefix'
        },
        'IncludedObjectVersions': 'All',
        'OptionalFields': {
            'Field': [
                'Size',
                'LastModifiedDate',
                'ETag',
                'StorageClass',
                'IsMultipartUploaded',
                'ReplicationStatus'
            ]
        },
        'Schedule': {
            'Frequency': 'Daily'
        }
    }
    response = client.put_bucket_inventory(
        Bucket=test_bucket,
        Id='test',
        InventoryConfiguration=inventory_config
    )
    # wait for sync
    # get inventory
    time.sleep(4)
    response = client.get_bucket_inventory(
        Bucket=test_bucket,
        Id='test'
    )
    # delete inventory
    response = client.delete_bucket_inventory(
        Bucket=test_bucket,
        Id='test'
    )


def test_put_get_delete_bucket_tagging():
    """测试设置获取删除bucket标签"""
    tagging_config = {
        'TagSet': {
            'Tag': [
                {
                    'Key': 'key0',
                    'Value': 'value0'
                }
            ]
        }
    }
    response = client.put_bucket_tagging(
        Bucket=test_bucket,
        Tagging=tagging_config
    )
    # wait for sync
    # get tagging
    time.sleep(1)
    response = client.get_bucket_tagging(
        Bucket=test_bucket
    )
    assert tagging_config == response
    # delete tagging
    response = client.delete_bucket_tagging(
        Bucket=test_bucket
    )


def _test_put_get_delete_bucket_origin():
    """测试设置获取删除bucket回源域名"""
    origin_config = {}
    response = client.put_bucket_origin(
        Bucket=test_bucket,
        OriginConfiguration=origin_config
    )
    # wait for sync
    # get origin
    time.sleep(4)
    response = client.get_bucket_origin(
        Bucket=test_bucket
    )
    # delete origin
    response = client.delete_bucket_origin(
        Bucket=test_bucket
    )


if __name__ == "__main__":
    setUp()
    """
    test_put_object_enable_md5()
    test_upload_with_server_side_encryption()
    test_upload_empty_file()
    test_put_get_delete_object_10MB()
    test_put_get_versioning()
    test_put_get_delete_replication()
    test_upload_part_copy()
    test_upload_file_multithreading()
    test_copy_file_automatically()
    test_copy_10G_file_in_same_region()
    test_list_objects()
    test_use_get_auth()
    test_put_get_bucket_logging()
    test_put_get_delete_website()
    test_put_get_bucket_policy()
    test_put_file_like_object()
    test_put_chunked_object()
    """
    test_put_get_delete_bucket_inventory()
    tearDown()
