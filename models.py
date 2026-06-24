from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Author:
    user_id: str
    nickname: str
    avatar: Optional[str] = None


@dataclass
class NoteImage:
    index: int
    url: str
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class NoteStats:
    liked_count: Optional[str] = None
    collected_count: Optional[str] = None
    comment_count: Optional[str] = None
    share_count: Optional[str] = None


@dataclass
class Note:
    note_id: str
    title: str
    content: str
    note_type: str = "normal"
    publish_time: Optional[int] = None
    publish_date: Optional[str] = None
    author: Optional[Author] = None
    tags: List[str] = field(default_factory=list)
    images: List[NoteImage] = field(default_factory=list)
    stats: Optional[NoteStats] = None
    ip_location: Optional[str] = None
    source_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "content": self.content,
            "note_type": self.note_type,
            "publish_time": self.publish_time,
            "publish_date": self.publish_date,
            "author": {
                "user_id": self.author.user_id,
                "nickname": self.author.nickname,
                "avatar": self.author.avatar,
            } if self.author else None,
            "tags": self.tags,
            "images": [
                {"index": img.index, "url": img.url, "width": img.width, "height": img.height}
                for img in self.images
            ],
            "stats": {
                "liked_count": self.stats.liked_count,
                "collected_count": self.stats.collected_count,
                "comment_count": self.stats.comment_count,
                "share_count": self.stats.share_count,
            } if self.stats else None,
            "ip_location": self.ip_location,
            "source_url": self.source_url,
        }
