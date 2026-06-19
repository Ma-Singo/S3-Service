"""
S3 storage service

Upload strategy
    Small files (< MULTIPART THRESHOLD = 50 MB)
        put_object: single request, low latency

    Large files (> MULTIPART THRESHOLD )
        Multipart upload: file is slit into PART_SIZE chunks (default 50 MB)
                        uploaded in parallel

"""

import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import logger


class S3Service:
    def __init__(self):
        self._bucket = settings.AWS_S3_BUCKET

        kwargs: dict = dict(
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        if settings.AWS_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL

        self._client = boto3.client("s3", **kwargs)

    def ensure_buckets_exist(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=bucket)
            logger.info("s3_bucket_created", bucket=self._bucket)


    def _upload(
        self,
        data: bytes,
        key: str,
        mime_type: str,
        extra_metadata: dict | None = None,
    ) -> None:
        """
        Choose put or multipart depending on file size
        Raise on any unrecoverable error after retries
        """
        size = len(data)
        if size < settings.MULTIPART_THRESHOLD:
            self._put_object(data, key, mime_type, extra_metadata)
        else:
            self._multipart_upload(data, key, mime_type, extra_metadata)

    def _put_object(
        self, data: bytes, key: str, mime_type: str, extra_metadata: dict
    ) -> None:
        kwargs: dict = dict(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=mime_type,
            ServerSideEncryption="AES256",
        )

        if extra_metadata:
            kwargs["Metadata"] = extra_metadata

        self._client.put_object(**kwargs)
        logger.info(
            "s3_put_object",
            bucket=self._bucket,
            key=key,
            size_mb=round(len(data) / 1024 / 1024, 2),
        )

    def _multipart_upload(
        self, data: bytes, key: str, mime_type: str, extra_metadata: dict
    ) -> None:
        """Multipart upload for larger files"""
        import math
        from concurrent.futures import ThreadPoolExecutor, as_completed

        size = len(data)
        part_count = math.ceil(size / settings.PART_SIZE)
        upload_id = None

        logger.info(
            "s3_multipart_start",
            bucket=self._bucket,
            key=key,
            size_mb=round(len(data) / 1024 / 1024, 2),
            parts=part_count,
        )
        create_kwargs: dict = dict(
            Bucket=self._bucket, Key=key, ContentType=mime_type, ServerSideEncryption="AES256"
        )
        if extra_metadata:
            create_kwargs["Metadata"] = extra_metadata
        try:
            response = self._client.create_multipart_upload(**create_kwargs)
            upload_id = response["UploadId"]

            parts: list[dict] = [{} for _ in range(part_count)]

            def _upload_part(part_number: int) -> dict:
                """Upload one chunk
                :return 'PartNumber': n, 'ETag': '...'
                """
                start = (part_count - 1) * settings.PART_SIZE
                end = min(start + settings.PART_SIZE, size)
                chunk = data[start:end]

                response = self._client.upload_part(
                    Bucket=self._bucket,
                    Key=key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=chunk,
                )
                logger.debug(
                    "s3_part_uploaded",
                    key=key,
                    part_number=part_number,
                    part_count=part_count,
                    chunk_mb=round(len(chunk) / 1024 / 1024, 2),
                )
                return {"PartNumber": part_number, "ETag": response["ETag"]}

            with ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENCY) as pool:
                futures = {
                    pool.submit(_upload_part, n): n for n in range(1, part_count + 1)
                }

                for future in as_completed(futures):
                    result = future.result()
                    parts[result["PartNumber"] - 1] = result

            self._client.complete_multipart_upload(
                Bucket=self._bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )

            logger.info(
                "s3_multipart_complete",
                bucket=self._bucket,
                key=key,
                size_mb=round(len(data) / 1024 / 1024, 2),
                parts=part_count,
            )

            upload_id = None

        finally:
            if upload_id is not None:
                try:
                    self._client.abort_multipart_upload(
                        Bucket=self._bucket, Key=key, UploadId=upload_id
                    )
                    logger.warning("s3_multipart_aborted", bucket=self._bucket, key=key)
                except Exception as abort_exc:
                    logger.error(
                        "s3_multipart_abort_failed",
                        bucket=self._bucket,
                        key=key,
                        error=str(abort_exc),
                    )


    def upload_raw(
        self, data: bytes, filename: str, mime_type: str
    ) -> str:
        ext = Path(filename).suffix.lower() or ".bin"
        key = f"quotes/{uuid.uuid4()}/source/{filename}{ext}"
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=mime_type,
            ServerSideEncryption="AES256",
            Metadata={"original_filename": filename},
        )
        logger.info("s3_raw_uploaded", key=key, bytes=len(data))
        return key


    def download(self, key: str) -> bytes:
        """Download an object and return its raw bytes"""
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()


    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def check_health(self) -> bool:
        try:
            self._client.list_buckets()
            return True
        except Exception:
            return False


storage = S3Service()
