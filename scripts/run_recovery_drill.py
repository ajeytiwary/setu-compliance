"""Upload a consistent tenant backup, download it, restore it, and record proof."""
from __future__ import annotations

import json
import os

from app.recovery import backup_and_drill


def main() -> None:
    import boto3
    tenant = os.environ['EUROSETU_DEPLOYMENT_TENANT']
    bucket = os.environ['EUROSETU_BACKUP_BUCKET']
    endpoint = os.getenv('EUROSETU_BACKUP_S3_ENDPOINT')
    if endpoint and os.getenv('EUROSETU_ENV') == 'production' and not endpoint.startswith('https://'):
        raise ValueError('Production S3 endpoint must use HTTPS')
    client = boto3.client('s3', endpoint_url=endpoint or None)
    result = backup_and_drill(tenant, bucket, os.getenv('EUROSETU_BACKUP_PREFIX', 'eurosetu'), client)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
