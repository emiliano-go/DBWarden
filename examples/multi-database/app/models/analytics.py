from sqlalchemy import Column, Int64, String, Date, DateTime
from sqlalchemy.orm import declarative_base
from dbwarden import CHTableMeta, CHColumnMeta, ChEngineSpec, ChIndexSpec, ProjectionSpec

Base = declarative_base()


class PageView(Base):
    __tablename__ = "page_views"

    id = Column(Int64, primary_key=True)
    url = Column(String, nullable=False)
    user_id = Column(Int64, nullable=True)
    viewed_at = Column(DateTime, nullable=False)
    event_date = Column(Date, nullable=False)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by = ["event_date", "id"]
        ch_partition_by = "toYYYYMM(event_date)"
        ch_ttl = ["event_date + toIntervalYear(1) DELETE"]
        ch_projections = [
            ProjectionSpec(
                "by_url",
                "SELECT url, count() GROUP BY url",
            ),
        ]
        ch_indexes = [
            ChIndexSpec(
                "ix_url_bloom",
                ["url"],
                type="bloom_filter",
                granularity=1,
            ),
        ]

        class url(CHColumnMeta):
            ch_codec = "ZSTD(3)"
