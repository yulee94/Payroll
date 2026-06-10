# 자료함 cloud-native intake architecture

Last updated: 2026-06-10

## Decision

자료함 is Bitween's governed object archive and business-data intake workbench.
It accepts any file, stores all files/originals/attachments/blobs in
self-hosted RustFS, records metadata, staging, review, and admitted business
data in self-hosted PostgreSQL, and only admits extracted rows into HR/payroll
relational tables after validation and human review.

RustFS is the self-hosted S3-compatible object/blob store for license and
Rust-stack fit. PostgreSQL is the relational system of record for metadata,
staging, review, and admitted business data.

## Benchmark evidence

Official/upstream sources reviewed:

- RustFS introduction: https://docs.rustfs.com/concepts/introduction.html
  - RustFS is positioned as Apache-2.0, S3-compatible, Rust-based distributed
    object storage.
- RustFS Linux installation: https://docs.rustfs.com/installation/linux/
  - RustFS is deployable as a self-hosted object-storage service.
- RustFS license: https://github.com/rustfs/rustfs/blob/main/LICENSE
  - Confirms Apache-2.0 licensing.
- OWASP File Upload Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
  - Uploads are untrusted. Apply extension/type/signature validation, generated
    filenames, file-size limits, authorization, storage isolation, malware/CDR
    controls, and manual review where needed.
- PostgreSQL binary / large-object documentation:
  - https://www.postgresql.org/docs/current/datatype-binary.html
  - https://www.postgresql.org/docs/current/storage-toast.html
  - https://www.postgresql.org/docs/current/largeobjects.html
  - PostgreSQL can store binary data, but Bitween should keep large uploaded
    originals in RustFS and keep PostgreSQL for metadata, staging tables,
    admission state, mappings, tasks, audit, and canonical HR/payroll rows.
- AWS S3 event notifications:
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html
  and
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html
  - Object-created events feed asynchronous processing destinations. Delivery
    can be duplicated or out of order, so Bitween intake must be idempotent.
- Snowflake load validation/history:
  - https://docs.snowflake.com/en/sql-reference/sql/copy-into-table
  - https://docs.snowflake.com/en/sql-reference/functions/validate
  - https://docs.snowflake.com/en/sql-reference/functions/copy_history
  - Mature ingestion surfaces expose validation results, error handling, and
    load history instead of silently accepting faulty rows.
- Databricks Auto Loader:
  - https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/
  - https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/schema
  - Best-in-class ingestion expects schema drift, rescues unexpected data, and
    separates evolution decisions from blind admission.
- Document repository patterns:
  - Box metadata/versioning/collaboration:
    https://support.box.com/hc/en-us/articles/360044196173-Using-Metadata,
    https://support.box.com/hc/en-us/articles/360043697054-Accessing-Version-History,
    https://developer.box.com/reference/resources/collaboration
  - Google Drive metadata/revisions/sharing:
    https://developers.google.com/workspace/drive/api/guides/file-metadata,
    https://developers.google.com/workspace/drive/api/guides/manage-revisions,
    https://developers.google.com/workspace/drive/api/guides/manage-sharing
  - SharePoint versioning/sensitivity/metadata:
    https://support.microsoft.com/en-us/office/how-versioning-works-in-lists-and-libraries-0f6cd105-974f-44a4-aadb-43ac5bdfd247,
    https://learn.microsoft.com/en-us/sharepoint/document-library-version-history-limits,
    https://learn.microsoft.com/en-us/purview/sensitivity-labels-sharepoint-onedrive-files,
    https://learn.microsoft.com/en-us/sharepoint/managed-metadata
  - SAP Document Management:
    https://www.sap.com/products/technology-platform/document-management.html
  - Enterprise repositories treat file metadata, versions, permissions,
    sensitivity labels, retention limits, and sharing boundaries as first-class
    product objects.

## Target ingestion model

1. **Receive any file.**
   - Enforce authenticated uploader, tenant/legal-entity scope, request size
     limits, safe generated object keys, and disallowed executable policies.
   - Preserve original filename only as metadata, not as a storage key.
2. **Quarantine original in RustFS.**
   - Write to a quarantine bucket/prefix first: `rustfs://<bucket>/quarantine/...`.
   - Record checksum, size, content type, uploader, tenant, and object URI.
3. **Record intake state in PostgreSQL.**
   - `archive_intake`: one row per file/version.
   - `archive_intake_version`: version lineage and checksum history.
   - `archive_intake_issue`: missing data, ambiguous columns, anomalies,
     malware/CDR status, schema drift, and human guidance questions.
   - `archive_mapping_template`: tenant-approved HR/payroll column mappings.
4. **Extract only what is safe.**
   - CSV/XLSX/TXT get bounded sampling first.
   - ZIP is a container, not an automatically trusted folder tree. Store the
     original ZIP once in RustFS quarantine; create review rows only for safe
     inner CSV/TSV/TXT/XLSX members.
   - ZIP member extraction rejects absolute paths, drive letters, backslashes,
     `.`/`..` traversal, control characters, encrypted entries, symlinks, and
     unsupported file types before sampling.
   - ZIP extraction has per-entry, total extracted-byte, text-sample, and entry
     count caps. Unsupported or unsafe members remain preserved inside the
     immutable archived original and do not appear as operator review rows.
   - Unknown binary files remain archive blobs unless a classifier or user mapping
     marks them as HR/payroll source material.
   - Zip/XML/spreadsheet extraction is bounded to avoid zip bombs.
5. **Classify and stage.**
   - HR files stage into HR staging tables.
   - Payroll files stage into payroll input staging tables.
   - Ambiguous tabular files become mapping tasks.
   - Non-tabular files remain linked archive objects.
6. **Surface human review tasks.**
   - Ask operational questions in the UI: which business area, what a column
     means, why required data is missing, whether an anomaly is valid.
   - Do not expose RustFS/PostgreSQL/source internals to payroll/HR operators.
7. **Admit only after approval.**
   - Approved staging rows move to canonical PostgreSQL HR/payroll tables through
     auditable Rust service commands.
   - Admission stores who approved, mappings used, row counts, exceptions, and
     rollback references.
   - Before every canonical write, PostgreSQL captures row-level recovery
     metadata (`before_payload`/`after_payload`, row hash, target table,
     business key, actor, timestamp). These are JSON deltas and checksums only;
     PostgreSQL must not store workbook/file binaries, `bytea` blobs, or binary
     snapshots.
   - Source workbook/file versions remain immutable RustFS objects referenced by
     `archive_intake_version.object_uri`. Source-file sync after admission or
     rollback is represented by `archive_source_sync` rows that point from the
     immutable source object to a derived RustFS object URI when a generated
     workbook version exists.
   - Rollback restores selected row-level recovery points for HR employee,
     attendance, and payroll input rows, marks consumed recovery points as
     restored, and queues a source-file sync item so linked workbook views can be
     regenerated without overwriting the original upload.
8. **Retain and govern.**
   - Apply tenant-scoped permissions, sensitivity labels, audit logs, legal hold,
     retention/deletion policy, and version limits.

## UI implications

- 자료함 is not a technical storage screen. It should show:
  - files awaiting review,
  - files safely archived,
  - mapping/anomaly questions needing a human answer,
  - admitted HR/payroll data and rollback evidence.
- Operators should see business-language prompts, not object-store/database
  implementation details.
- Numbered stub-like workflow cards are unacceptable; archive and intake queues
  must show role-relevant work, review owner, action, and business status.
- Workflow remains the separate corporate logic/canvas/editor surface.
  전자결재/approval is signing/approval only and should not absorb intake routing
  or workflow editing.
- Upload can fail closed if RustFS is not configured; the UI should explain that
  the file was not received and invite a retry or admin setup path.

## Current implementation checkpoint

- `apps/bitween-platform-ui/preview/server.js` accepts multipart uploads,
  stores originals in RustFS through an S3-compatible signed PUT, samples text
  and XLSX safely, splits ZIP uploads into one review row per safe inner
  tabular file, skips unsafe traversal/symlink/encrypted/oversized ZIP members,
  and then calls the Rust/Buck2 intake target.
- `crates/payroll-api/src/bin/archive_intake_store.rs` records intake metadata,
  checksum, RustFS URI, business-family classification, PostgreSQL-staging
  readiness, guidance items, anomaly items, and ready HR/attendance/payroll
  sample rows translated into PostgreSQL staging payloads with row hashes.
  It also resolves selected open guidance/anomaly issues with auditable
  reviewer decisions and recomputes the intake's next action/readiness from the
  remaining open review work. Reviewed HR employee, HR attendance, and payroll
  input staging rows can now be admitted through a manager-gated `admit` action
  that upserts `bitween_archive.hr_employee_staging` into
  `bitween_hr.employee`, `bitween_archive.hr_attendance_staging` into
  `bitween_hr.attendance_record`, and `bitween_archive.payroll_input_staging`
  into `bitween_payroll.payroll_input`; rejected rows are marked invalid,
  `archive_admission_audit` records row counts/rollback evidence, row-level
  `archive_admission_recovery_point` records preserve reversible JSON metadata
  only, `archive_source_sync` queues linked source-workbook regeneration without
  storing binary snapshots, and the intake closes as admitted/rejected rather
  than keeping a browser-only approval. Manager-gated rollback is live-wired for
  admitted/rejected intakes and can restore all available recovery points or a
  selected recovery point while re-opening staging rows for further review.
- The preview 자료함 board now shows review counts and business destinations,
  source versions, recovery points, source-file sync state, and business actions.
  The operator can mark eligible guidance/anomaly items reviewed, admit reviewed
  HR/payroll rows, or restore an available recovery point through
  authorization-gated HTTP routes instead of editing local state in the browser.
- The local preview metadata store remains a hermetic review adapter only behind
  `BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true`. Production write paths use the
  PostgreSQL schema and Rust service migrations above; full production
  persistence still needs a repository-owned PostgreSQL/RustFS fixture before
  real tenant data is admitted.
- ZIP UX/security addendum: the browser workbench keeps the review queue visible
  when a malicious or over-limit ZIP fails, shows Korean recovery copy that
  points to archive storage/file-size/ZIP-entry-count checks, and the hermetic
  archive verifier exercises actual UI usage stories for normal ZIP upload,
  empty readable files, mapping review, traversal-member suppression, and
  over-limit ZIP failure.
