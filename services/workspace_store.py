"""
services/workspace_store.py - 개인·회사 업무 데이터 (세션·계정 격리)
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from core.paths import app_data_dir
from core.session_service import UserSession, require_session
from core.user_store import get_user, list_users_for_tenant

WORKSPACE_ROOT = app_data_dir() / "workspace"


class AccessDenied(PermissionError):
    pass


def _today() -> str:
    return date.today().isoformat()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _assert_session(session: UserSession | None = None) -> UserSession:
    return session or require_session()


def _user_dir(sess: UserSession) -> Path:
    return WORKSPACE_ROOT / sess.tenant_id / "users" / sess.user_id


def _user_file(sess: UserSession, name: str) -> Path:
    d = _user_dir(sess)
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def _tenant_messages_dir(tenant_id: str) -> Path:
    d = WORKSPACE_ROOT / tenant_id / "messages"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tenant_company_dir(tenant_id: str) -> Path:
    d = WORKSPACE_ROOT / tenant_id / "company"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _thread_id(user_a: str, user_b: str) -> str:
    return "__".join(sorted([user_a, user_b]))


def _load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _assert_participant(sess: UserSession, participants: list[str]) -> None:
    if sess.user_id not in participants:
        raise AccessDenied("이 대화에 접근할 수 없습니다.")


# --- To-Do ---


def list_todos(session: UserSession | None = None) -> list[dict[str, Any]]:
    sess = _assert_session(session)
    raw = _load_json(_user_file(sess, "todos.json"), {"items": []})
    items = raw.get("items") if isinstance(raw, dict) else []
    if not isinstance(items, list):
        return []
    return sorted(items, key=lambda x: (not x.get("done"), x.get("due_date") or "", x.get("created_at") or ""))


def add_todo(title: str, *, due_date: str = "", session: UserSession | None = None) -> dict[str, Any]:
    sess = _assert_session(session)
    title = str(title or "").strip()
    if not title:
        raise ValueError("할 일 내용을 입력하세요.")
    path = _user_file(sess, "todos.json")
    raw = _load_json(path, {"items": []})
    items: list[dict[str, Any]] = list(raw.get("items") or [])
    item = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "due_date": str(due_date or "").strip(),
        "done": False,
        "created_at": _now_iso(),
    }
    items.append(item)
    _save_json(path, {"items": items})
    return item


def toggle_todo(todo_id: str, session: UserSession | None = None) -> None:
    sess = _assert_session(session)
    path = _user_file(sess, "todos.json")
    raw = _load_json(path, {"items": []})
    items: list[dict[str, Any]] = list(raw.get("items") or [])
    for it in items:
        if it.get("id") == todo_id:
            it["done"] = not bool(it.get("done"))
            break
    _save_json(path, {"items": items})


def delete_todo(todo_id: str, session: UserSession | None = None) -> None:
    sess = _assert_session(session)
    path = _user_file(sess, "todos.json")
    raw = _load_json(path, {"items": []})
    items = [it for it in (raw.get("items") or []) if it.get("id") != todo_id]
    _save_json(path, {"items": items})


def todos_due_today(session: UserSession | None = None) -> list[dict[str, Any]]:
    today = _today()
    return [t for t in list_todos(session) if not t.get("done") and (t.get("due_date") or "") <= today]


def _user_file_for(user_id: str, tenant_id: str, name: str) -> Path:
    d = WORKSPACE_ROOT / tenant_id / "users" / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def add_todo_for_user(
    user_id: str,
    tenant_id: str,
    title: str,
    *,
    due_date: str = "",
    source: str = "",
    document_id: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = str(title or "").strip()
    if not title or not user_id or not tenant_id:
        raise ValueError("할 일 등록 정보가 부족합니다.")
    path = _user_file_for(user_id, tenant_id, "todos.json")
    raw = _load_json(path, {"items": []})
    items: list[dict[str, Any]] = list(raw.get("items") or [])
    extra_payload = dict(extra or {})
    source_key = str(extra_payload.get("source_key") or "").strip()
    if not source_key and source and document_id:
        source_key = f"{source}:{document_id}:{title}"
    if source_key:
        for it in items:
            if str(it.get("source_key") or "") != source_key:
                continue
            it.update(
                {
                    "title": title,
                    "due_date": str(due_date or "").strip(),
                    "source": source,
                    "document_id": document_id,
                    "source_key": source_key,
                    "updated_at": _now_iso(),
                }
            )
            it.update(extra_payload)
            _save_json(path, {"items": items})
            return it
    item = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "due_date": str(due_date or "").strip(),
        "done": False,
        "created_at": _now_iso(),
        "source": source,
        "document_id": document_id,
    }
    if source_key:
        item["source_key"] = source_key
    if extra_payload:
        item.update(extra_payload)
    items.append(item)
    _save_json(path, {"items": items})
    return item


def add_calendar_event_for_user(
    user_id: str,
    tenant_id: str,
    title: str,
    event_date: str,
    *,
    end_date: str = "",
    source: str = "",
    document_id: str = "",
    source_key: str = "",
) -> dict[str, Any]:
    title = str(title or "").strip()
    event_date = str(event_date or "").strip()[:10]
    if not title or not event_date or not user_id or not tenant_id:
        raise ValueError("일정 등록 정보가 부족합니다.")
    path = _user_file_for(user_id, tenant_id, "calendar.json")
    raw = _load_json(path, {"events": []})
    events: list[dict[str, Any]] = list(raw.get("events") or [])
    source_key = str(source_key or "").strip()
    if not source_key and source and document_id:
        source_key = f"{source}:{document_id}:{title}:{event_date}"
    if source_key:
        for ev in events:
            if str(ev.get("source_key") or "") != source_key:
                continue
            ev.update(
                {
                    "title": title,
                    "date": event_date,
                    "end_date": str(end_date or "").strip()[:10],
                    "all_day": True,
                    "source": source,
                    "document_id": document_id,
                    "source_key": source_key,
                    "updated_at": _now_iso(),
                }
            )
            _save_json(path, {"events": events})
            return ev
    ev = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "date": event_date,
        "end_date": str(end_date or "").strip()[:10],
        "all_day": True,
        "created_at": _now_iso(),
        "source": source,
        "document_id": document_id,
    }
    if source_key:
        ev["source_key"] = source_key
    events.append(ev)
    _save_json(path, {"events": events})
    return ev


# --- Calendar ---


def list_calendar_events(
    year: int,
    month: int,
    session: UserSession | None = None,
) -> list[dict[str, Any]]:
    sess = _assert_session(session)
    raw = _load_json(_user_file(sess, "calendar.json"), {"events": []})
    events = raw.get("events") if isinstance(raw, dict) else []
    prefix = f"{year:04d}-{month:02d}"
    out = []
    for ev in events if isinstance(events, list) else []:
        d = str(ev.get("date") or "")
        if d.startswith(prefix):
            out.append(ev)
    return sorted(out, key=lambda x: x.get("date") or "")


def add_calendar_event(
    title: str,
    event_date: str,
    *,
    all_day: bool = True,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = _assert_session(session)
    title = str(title or "").strip()
    if not title:
        raise ValueError("일정 제목을 입력하세요.")
    event_date = str(event_date or "").strip()
    if len(event_date) < 10:
        raise ValueError("날짜(YYYY-MM-DD)를 입력하세요.")
    path = _user_file(sess, "calendar.json")
    raw = _load_json(path, {"events": []})
    events: list[dict[str, Any]] = list(raw.get("events") or [])
    ev = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "date": event_date[:10],
        "all_day": all_day,
        "created_at": _now_iso(),
    }
    events.append(ev)
    _save_json(path, {"events": events})
    return ev


# --- Mail (personal inbox) ---

# COSS GW 메일함 폴더 대응 (개인 메모함 — 외부 SMTP 미연동)
MAIL_FOLDERS: tuple[tuple[str, str], ...] = (
    ("inbox", "받은 메일"),
    ("unread", "안읽은 메일"),
    ("sent", "보낸 메일"),
    ("draft", "임시보관"),
)


def _normalize_mail_folder(folder: str | None) -> str:
    fid = str(folder or "inbox").strip().lower()
    if fid in ("inbox", "sent", "draft"):
        return fid
    if fid == "unread":
        return "unread"
    return "inbox"


def list_mail(
    session: UserSession | None = None,
    limit: int = 50,
    *,
    folder: str | None = None,
) -> list[dict[str, Any]]:
    sess = _assert_session(session)
    raw = _load_json(_user_file(sess, "mail.json"), {"messages": []})
    msgs = raw.get("messages") if isinstance(raw, dict) else []
    if not isinstance(msgs, list):
        return []
    fid = _normalize_mail_folder(folder) if folder else "inbox"
    if fid == "unread":
        msgs = [m for m in msgs if not m.get("read")]
    else:
        msgs = [m for m in msgs if (m.get("folder") or "inbox") == fid]
    msgs = sorted(msgs, key=lambda x: x.get("received_at") or "", reverse=True)
    return msgs[:limit]


def unread_mail_count(session: UserSession | None = None) -> int:
    return len(list_mail(session, folder="unread"))


def add_mail(
    subject: str,
    body: str,
    *,
    sender: str = "",
    folder: str = "inbox",
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = _assert_session(session)
    path = _user_file(sess, "mail.json")
    raw = _load_json(path, {"messages": []})
    msgs: list[dict[str, Any]] = list(raw.get("messages") or [])
    mail_folder = _normalize_mail_folder(folder)
    if mail_folder == "unread":
        mail_folder = "inbox"
    msg = {
        "id": uuid.uuid4().hex[:12],
        "subject": str(subject or "").strip() or "(제목 없음)",
        "body": str(body or "").strip(),
        "sender": str(sender or "").strip() or "내부",
        "folder": mail_folder,
        "read": mail_folder != "inbox",
        "received_at": _now_iso(),
    }
    msgs.append(msg)
    _save_json(path, {"messages": msgs})
    return msg


def mark_mail_read(mail_id: str, session: UserSession | None = None) -> None:
    sess = _assert_session(session)
    path = _user_file(sess, "mail.json")
    raw = _load_json(path, {"messages": []})
    msgs: list[dict[str, Any]] = list(raw.get("messages") or [])
    for m in msgs:
        if m.get("id") == mail_id:
            m["read"] = True
            break
    _save_json(path, {"messages": msgs})


# --- Messenger (DM, same tenant only) ---


def _thread_path(tenant_id: str, thread_id: str) -> Path:
    return _tenant_messages_dir(tenant_id) / f"{thread_id}.json"


def _compliance_audit_path(tenant_id: str) -> Path:
    return _tenant_messages_dir(tenant_id) / "_compliance_audit.json"


def _append_compliance_audit(tenant_id: str, event: dict[str, Any]) -> None:
    """감사·컴플라이언스용 append-only 로그 (메시지 본문은 스레드 파일에 보존)."""
    path = _compliance_audit_path(tenant_id)
    raw = _load_json(path, {"events": []})
    events: list[dict[str, Any]] = list(raw.get("events") or [])
    events.append(
        {
            "id": uuid.uuid4().hex[:12],
            "at": _now_iso(),
            **event,
        }
    )
    _save_json(path, {"events": events})


def _is_message_visible_to_user(msg: dict[str, Any], user_id: str) -> bool:
    """사용자별 '나에게서만 삭제' 가시성. 미설정 시 기본 표시."""
    vis = msg.get("user_visibility")
    if not isinstance(vis, dict):
        return True
    entry = vis.get(user_id)
    if not isinstance(entry, dict):
        return True
    return bool(entry.get("visible", True))


def _mark_message_hidden_for_user(msg: dict[str, Any], user_id: str) -> None:
    """서버 스레드 파일에 soft-delete 메타만 기록 (본문·원본 필드는 유지)."""
    vis = msg.setdefault("user_visibility", {})
    if not isinstance(vis, dict):
        vis = {}
        msg["user_visibility"] = vis
    vis[user_id] = {
        "visible": False,
        "deleted_at": _now_iso(),
        "deleted_by": user_id,
    }


def _visible_messages(messages: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
    return [m for m in messages if _is_message_visible_to_user(m, user_id)]


def list_message_threads(session: UserSession | None = None) -> list[dict[str, Any]]:
    sess = _assert_session(session)
    msg_dir = _tenant_messages_dir(sess.tenant_id)
    threads: list[dict[str, Any]] = []
    for path in msg_dir.glob("*.json"):
        raw = _load_json(path, {})
        participants = raw.get("participants") if isinstance(raw, dict) else []
        if not isinstance(participants, list) or sess.user_id not in participants:
            continue
        messages = raw.get("messages") if isinstance(raw, dict) else []
        if not isinstance(messages, list):
            messages = []
        visible = _visible_messages(messages, sess.user_id)
        last = visible[-1] if visible else {}
        other_ids = [p for p in participants if p != sess.user_id]
        other_names = []
        for oid in other_ids:
            u = get_user(oid)
            other_names.append(u.display_name if u else oid[:8])
        threads.append(
            {
                "thread_id": path.stem,
                "participants": participants,
                "other_label": ", ".join(other_names) or "대화",
                "last_text": str(last.get("text") or ""),
                "last_at": str(last.get("sent_at") or ""),
                "unread": sum(
                    1
                    for m in visible
                    if not m.get("read") and m.get("sender_id") != sess.user_id
                ),
            }
        )
    return sorted(threads, key=lambda t: t.get("last_at") or "", reverse=True)


def get_thread_messages(
    other_user_id: str,
    session: UserSession | None = None,
) -> list[dict[str, Any]]:
    sess = _assert_session(session)
    other = get_user(other_user_id)
    if other is None or other.tenant_id != sess.tenant_id:
        raise AccessDenied("같은 고객사 사용자에게만 메시지를 보낼 수 있습니다.")
    if other.user_id == sess.user_id:
        raise ValueError("자신에게는 메시지를 보낼 수 없습니다.")
    tid = _thread_id(sess.user_id, other.user_id)
    path = _thread_path(sess.tenant_id, tid)
    raw = _load_json(
        path,
        {"participants": sorted([sess.user_id, other.user_id]), "messages": []},
    )
    _assert_participant(sess, list(raw.get("participants") or []))
    msgs = raw.get("messages") if isinstance(raw, dict) else []
    if not isinstance(msgs, list):
        return []
    return _visible_messages(msgs, sess.user_id)


def send_message(
    other_user_id: str,
    text: str,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = _assert_session(session)
    text = str(text or "").strip()
    if not text:
        raise ValueError("메시지를 입력하세요.")
    other = get_user(other_user_id)
    if other is None or other.tenant_id != sess.tenant_id:
        raise AccessDenied("같은 고객사 사용자에게만 메시지를 보낼 수 있습니다.")
    tid = _thread_id(sess.user_id, other.user_id)
    path = _thread_path(sess.tenant_id, tid)
    raw = _load_json(
        path,
        {"participants": sorted([sess.user_id, other.user_id]), "messages": []},
    )
    participants = sorted([sess.user_id, other.user_id])
    raw["participants"] = participants
    messages: list[dict[str, Any]] = list(raw.get("messages") or [])
    msg = {
        "id": uuid.uuid4().hex[:12],
        "sender_id": sess.user_id,
        "text": text,
        "sent_at": _now_iso(),
        "read": False,
    }
    messages.append(msg)
    raw["messages"] = messages
    _save_json(path, raw)
    return msg


def get_thread_messages_all(
    other_user_id: str,
    session: UserSession | None = None,
) -> list[dict[str, Any]]:
    """컴플라이언스·감사용: soft-delete 여부와 관계없이 스레드의 전체 메시지."""
    sess = _assert_session(session)
    other = get_user(other_user_id)
    if other is None or other.tenant_id != sess.tenant_id:
        raise AccessDenied("같은 고객사 사용자에게만 메시지를 보낼 수 있습니다.")
    tid = _thread_id(sess.user_id, other.user_id)
    path = _thread_path(sess.tenant_id, tid)
    raw = _load_json(path, {})
    _assert_participant(sess, list(raw.get("participants") or []))
    msgs = raw.get("messages") if isinstance(raw, dict) else []
    return msgs if isinstance(msgs, list) else []


def delete_message_for_user(
    message_id: str,
    other_user_id: str,
    session: UserSession | None = None,
) -> None:
    """
    단일 메시지를 요청 사용자 채팅함에서만 숨김 (per-user soft-delete).
    상대방·서버 원본 기록은 유지되며 감사 로그에 삭제 이벤트가 남습니다.
    """
    sess = _assert_session(session)
    message_id = str(message_id or "").strip()
    if not message_id:
        raise ValueError("삭제할 메시지를 선택하세요.")
    other = get_user(other_user_id)
    if other is None or other.tenant_id != sess.tenant_id:
        raise AccessDenied("같은 고객사 사용자에게만 메시지를 보낼 수 있습니다.")
    tid = _thread_id(sess.user_id, other.user_id)
    path = _thread_path(sess.tenant_id, tid)
    raw = _load_json(path, {})
    _assert_participant(sess, list(raw.get("participants") or []))
    messages: list[dict[str, Any]] = list(raw.get("messages") or [])
    target = next((m for m in messages if m.get("id") == message_id), None)
    if target is None:
        raise ValueError("메시지를 찾을 수 없습니다.")
    if not _is_message_visible_to_user(target, sess.user_id):
        return
    _mark_message_hidden_for_user(target, sess.user_id)
    raw["messages"] = messages
    _save_json(path, raw)
    _append_compliance_audit(
        sess.tenant_id,
        {
            "action": "message_soft_delete",
            "thread_id": tid,
            "message_id": message_id,
            "actor_user_id": sess.user_id,
            "sender_id": target.get("sender_id"),
            "text_preview": str(target.get("text") or "")[:120],
        },
    )


def clear_thread_for_user(
    other_user_id: str,
    session: UserSession | None = None,
) -> int:
    """
    대화 스레드의 모든 메시지를 요청 사용자 화면에서만 숨김.
    서버 스레드 파일·감사 로그에는 원본과 삭제 이벤트가 보존됩니다.
    """
    sess = _assert_session(session)
    other = get_user(other_user_id)
    if other is None or other.tenant_id != sess.tenant_id:
        raise AccessDenied("같은 고객사 사용자에게만 메시지를 보낼 수 있습니다.")
    tid = _thread_id(sess.user_id, other.user_id)
    path = _thread_path(sess.tenant_id, tid)
    raw = _load_json(path, {})
    _assert_participant(sess, list(raw.get("participants") or []))
    messages: list[dict[str, Any]] = list(raw.get("messages") or [])
    hidden_ids: list[str] = []
    for msg in messages:
        if not _is_message_visible_to_user(msg, sess.user_id):
            continue
        mid = str(msg.get("id") or "")
        _mark_message_hidden_for_user(msg, sess.user_id)
        if mid:
            hidden_ids.append(mid)
    if not hidden_ids:
        return 0
    raw["messages"] = messages
    _save_json(path, raw)
    _append_compliance_audit(
        sess.tenant_id,
        {
            "action": "thread_clear_for_user",
            "thread_id": tid,
            "actor_user_id": sess.user_id,
            "message_ids": hidden_ids,
            "message_count": len(hidden_ids),
        },
    )
    return len(hidden_ids)


def list_compliance_audit_events(
    tenant_id: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """테넌트 메신저 감사 로그 (컴플라이언스 조회용)."""
    raw = _load_json(_compliance_audit_path(tenant_id), {"events": []})
    events = raw.get("events") if isinstance(raw, dict) else []
    if not isinstance(events, list):
        return []
    return list(reversed(events[-limit:]))


def mark_thread_read(other_user_id: str, session: UserSession | None = None) -> None:
    sess = _assert_session(session)
    tid = _thread_id(sess.user_id, other_user_id)
    path = _thread_path(sess.tenant_id, tid)
    raw = _load_json(path, {})
    _assert_participant(sess, list(raw.get("participants") or []))
    for m in raw.get("messages") or []:
        if m.get("sender_id") != sess.user_id:
            m["read"] = True
    _save_json(path, raw)


def messenger_unread_total(session: UserSession | None = None) -> int:
    return sum(t.get("unread", 0) for t in list_message_threads(session))


# --- Company bulletin (tenant-wide, read-only for members) ---


def list_company_bulletins(session: UserSession | None = None) -> list[dict[str, Any]]:
    sess = _assert_session(session)
    raw = _load_json(_tenant_company_dir(sess.tenant_id) / "bulletins.json", {"items": []})
    items = raw.get("items") if isinstance(raw, dict) else []
    if not isinstance(items, list):
        return []
    return sorted(items, key=lambda x: x.get("posted_at") or "", reverse=True)


def seed_demo_mail_if_empty(session: UserSession | None = None) -> None:
    """첫 로그인 시 샘플 메일 (본인만 보임)."""
    sess = _assert_session(session)
    if list_mail(sess):
        return
    add_mail("Bitween 업무함 안내", "개인 메일함은 로그인한 계정만 열람할 수 있습니다.", sender="Bitween", session=sess)


def colleagues_except_self(session: UserSession | None = None) -> list[dict[str, str]]:
    sess = _assert_session(session)
    return [
        {"user_id": u.user_id, "display_name": u.display_name, "username": u.username}
        for u in list_users_for_tenant(sess.tenant_id)
        if u.user_id != sess.user_id
    ]
