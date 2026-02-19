@after

If wiki content storage becomes a performance or capacity problem, offload
large content to external block storage.

If the content field is null, fetch from external storage by hash. This allows
small content in the database with a migration path to offload large or
frequently duplicated content later.

- [ ] integrate block storage (MinIO for dev)
- [ ] accessor method checks external storage when content is null
- [ ] set size threshold, larger content stored externally

After implementation, migrate existing content.

- [ ] create a worker task to migrate existing large content
