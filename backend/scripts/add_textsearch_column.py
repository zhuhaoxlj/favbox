"""
快速修复脚本：为 SQLite 添加 textsearch 字段
"""

import sqlite3
import os

def add_textsearch_column():
    """为 SQLite 数据库添加 textsearch 列"""

    db_path = "./favbox.db"

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    print(f"🔧 正在修改数据库: {db_path}")

    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns = [row[1] for row in cursor.fetchall()]

        if "textsearch" in columns:
            print("✅ textsearch 字段已存在")
            conn.close()
            return True

        # 添加 textsearch 列
        print("📊 添加 textsearch 列...")
        cursor.execute("ALTER TABLE bookmarks ADD COLUMN textsearch TEXT")

        # 添加 ai_category_id 外键列（如果不存在）
        if "ai_category_id" not in columns:
            print("📊 添加 ai_category_id 列...")
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN ai_category_id INTEGER")
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_bookmarks_ai_category_id ON bookmarks(ai_category_id)")

        conn.commit()
        conn.close()

        print("✅ 数据库更新成功！")
        return True

    except Exception as e:
        print(f"❌ 更新失败: {e}")
        return False

if __name__ == "__main__":
    add_textsearch_column()
