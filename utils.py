import json
from pathlib import Path
from typing import Optional


def save_note_json(note, output_dir: str = "output") -> str:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    file_path = path / f"note_{note.note_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(note.to_dict(), f, indent=2, ensure_ascii=False)

    return str(file_path)


def save_notes_batch(notes, output_dir: str = "output") -> str:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    file_path = path / "notes_batch.json"
    data = [note.to_dict() for note in notes]
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return str(file_path)


def print_note_summary(note) -> None:
    print("\n" + "=" * 60)
    print("📝 笔记详情")
    print("=" * 60)
    print(f"  笔记ID: {note.note_id}")
    print(f"  标题: {note.title}")
    if note.author:
        print(f"  作者: {note.author.nickname} (ID: {note.author.user_id})")
    if note.publish_date:
        print(f"  发布时间: {note.publish_date}")
    print(f"  类型: {note.note_type}")
    print(f"  标签: {', '.join(note.tags) if note.tags else '无'}")
    print(f"  图片数: {len(note.images)}")
    if note.stats:
        print(f"  点赞: {note.stats.liked_count or 'N/A'}")
        print(f"  收藏: {note.stats.collected_count or 'N/A'}")
        print(f"  评论: {note.stats.comment_count or 'N/A'}")
    if note.ip_location:
        print(f"  IP属地: {note.ip_location}")
    print(f"  链接: {note.source_url}")
    print("-" * 60)
    print(f"  内容预览: {note.content[:150]}..." if len(note.content) > 150 else f"  内容: {note.content}")
    print("=" * 60 + "\n")
