"""Upload a consistent tenant backup, download it, restore it, and record proof."""
from __future__ import annotations

import json
import os
from urllib.parse import urlparse

from app.recovery import backup_and_drill


def main() -> None:
    import boto3
    tenant = os.environ['EUROSETU_DEPLOYMENT_TENANT']
    bucket = os.environ['EUROSETU_BACKUP_BUCKET']
    endpoint = os.getenv('EUROSETU_BACKUP_S3_ENDPOINT')
    if endpoint:
        parsed = urlparse(endpoint)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('S3 endpoint must be an HTTPS origin without a bucket path')
    r2 = bool(endpoint and urlparse(endpoint).hostname.endswith('.r2.cloudflarestorage.com'))
    client = boto3.client('s3', endpoint_url=endpoint or None, region_name='auto' if r2 else None)
    result = backup_and_drill(tenant, bucket, os.getenv('EUROSETU_BACKUP_PREFIX', 'eurosetu'), client,
                              server_side_encryption=None if r2 else 'AES256')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
