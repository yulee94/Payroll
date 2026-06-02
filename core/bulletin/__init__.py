"""core/bulletin - 그룹 공유 게시판 (공지)"""

from core.bulletin.service import (
    Announcement,
    BulletinVisibility,
    can_post_bulletin,
    can_post_group_wide,
    create_announcement,
    delete_announcement,
    format_scope_badge,
    format_scope_preview,
    get_announcement,
    list_announcements_for_viewer,
    list_group_sites,
    list_group_tenants,
    resolve_viewer_context,
    update_announcement,
)

__all__ = [
    "Announcement",
    "BulletinVisibility",
    "can_post_bulletin",
    "can_post_group_wide",
    "create_announcement",
    "delete_announcement",
    "format_scope_badge",
    "format_scope_preview",
    "get_announcement",
    "list_announcements_for_viewer",
    "list_group_sites",
    "list_group_tenants",
    "resolve_viewer_context",
    "update_announcement",
]
