import asyncio
from pathlib import Path
from typing import Any

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.interfaces import ProviderError
from app.core.types import StoredObject

# Un vídeo de ~10 MB sube en una sola petición: el multipart multiplicaría las operaciones de escritura de R2.
SINGLE_PUT = TransferConfig(multipart_threshold=256 * 1024 * 1024)


class R2Storage:
    provider = "r2"

    def __init__(
        self, account_id: str, access_key_id: str, secret_access_key: str, bucket: str, *, client: Any = None
    ):
        self._bucket = bucket
        self._s3 = client or boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
            config=Config(retries={"max_attempts": 3, "mode": "standard"}),
        )

    async def put_bytes(self, key: str, data: bytes, mime_type: str) -> StoredObject:
        await self._call(self._s3.put_object, Bucket=self._bucket, Key=key, Body=data, ContentType=mime_type)
        return StoredObject(key=key, file_size=len(data), mime_type=mime_type, provider=self.provider)

    async def put_file(self, key: str, path: Path, mime_type: str) -> StoredObject:
        await self._call(
            self._s3.upload_file, str(path), self._bucket, key,
            ExtraArgs={"ContentType": mime_type}, Config=SINGLE_PUT,
        )
        return StoredObject(key=key, file_size=path.stat().st_size, mime_type=mime_type, provider=self.provider)

    async def delete(self, key: str) -> None:
        await self._call(self._s3.delete_object, Bucket=self._bucket, Key=key)

    @staticmethod
    async def _call(fn, *args, **kwargs) -> None:
        try:
            await asyncio.to_thread(fn, *args, **kwargs)
        except (BotoCoreError, ClientError) as e:
            raise ProviderError(f"r2: {e}") from e
