## ADDED Requirements

### Requirement: Storage location constants are always defined
`settings.STATIC_LOCATION`, `settings.PUBLIC_MEDIA_LOCATION`, and `settings.PRIVATE_MEDIA_LOCATION` SHALL be defined unconditionally (not only inside the `STORAGE_AWS=True` branch). When `STORAGE_AWS=False` they SHALL fall back to `"static"`, `"media"`, and `"private"` (no `AWS_PROJECT_FOLDER` prefix). This avoids `AttributeError` if any code path imports `project.storage_backends` in dev.

#### Scenario: Local storage locations defined
- **WHEN** `.env.dev` has `STORAGE_AWS=False` and `AWS_PROJECT_FOLDER` is unset
- **THEN** `settings.STATIC_LOCATION == "static"`, `settings.PUBLIC_MEDIA_LOCATION == "media"`, `settings.PRIVATE_MEDIA_LOCATION == "private"`

### Requirement: Three S3 storage backends
`project/storage_backends.py` SHALL define `StaticStorage`, `PublicMediaStorage`, and `PrivateMediaStorage` classes extending `S3Boto3Storage`. `StaticStorage` SHALL use `location = settings.STATIC_LOCATION` and `default_acl = "public-read"`. `PublicMediaStorage` SHALL use `location = settings.PUBLIC_MEDIA_LOCATION`, `default_acl = "public-read"`, and `file_overwrite = False`. `PrivateMediaStorage` SHALL use `location = settings.PRIVATE_MEDIA_LOCATION`, `default_acl = "private"`, `file_overwrite = False`, and `custom_domain = False`.

#### Scenario: Backend classes importable
- **WHEN** Django starts with `STORAGE_AWS=True`
- **THEN** `from project.storage_backends import StaticStorage, PublicMediaStorage, PrivateMediaStorage` succeeds and all three reference `S3Boto3Storage`

### Requirement: S3 storage activation by env flag
`settings.STORAGES` SHALL use the S3 backends only when `STORAGE_AWS == "True"`. Otherwise the `default` backend SHALL be `django.core.files.storage.FileSystemStorage` and the `staticfiles` backend SHALL be `whitenoise.storage.CompressedManifestStaticFilesStorage`. When S3 is active, `STATIC_LOCATION`, `PUBLIC_MEDIA_LOCATION`, and `PRIVATE_MEDIA_LOCATION` SHALL be derived as `f"{AWS_PROJECT_FOLDER}/static"`, `f"{AWS_PROJECT_FOLDER}/media"`, and `f"{AWS_PROJECT_FOLDER}/private"` respectively.

#### Scenario: Local fallback
- **WHEN** `.env.dev` has `STORAGE_AWS=False`
- **THEN** `STORAGES["default"]["BACKEND"] == "django.core.files.storage.FileSystemStorage"`

#### Scenario: S3 active
- **WHEN** `.env.prod` has `STORAGE_AWS=True` and `AWS_PROJECT_FOLDER=clients`
- **THEN** `STATIC_LOCATION == "clients/static"`, `PUBLIC_MEDIA_LOCATION == "clients/media"`, `PRIVATE_MEDIA_LOCATION == "clients/private"`

### Requirement: Bucket and endpoint config
When `STORAGE_AWS=True`, settings SHALL read `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_CUSTOM_DOMAIN`, and `AWS_PROJECT_FOLDER` from the environment. `AWS_S3_OBJECT_PARAMETERS` SHALL be `{"CacheControl": "max-age=86400"}` and `AWS_DEFAULT_ACL` SHALL be `None`.

#### Scenario: DigitalOcean Spaces config
- **WHEN** `.env.prod` sets `AWS_S3_ENDPOINT_URL=https://sfo3.digitaloceanspaces.com` and `AWS_S3_REGION_NAME=sfo3`
- **THEN** uploads via `PublicMediaStorage` go to the `sfo3` region
