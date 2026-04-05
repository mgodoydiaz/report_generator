"""
models.py — Modelos ORM SQLAlchemy para todas las tablas.

Cada tabla con datos de negocio incluye org_id para multi-tenancy.
Las tablas de auth (organizations, users) son la base del sistema.
"""

from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database import Base


# =============================================================================
# AUTH & TENANCY
# =============================================================================

class Organization(Base):
    __tablename__ = "organizations"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    slug        = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    users       = relationship("User", back_populates="organization")
    pipelines   = relationship("Pipeline", back_populates="organization")
    metrics     = relationship("Metric", back_populates="organization")
    dimensions  = relationship("Dimension", back_populates="organization")
    indicators  = relationship("Indicator", back_populates="organization")
    specs       = relationship("Spec", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(200), default="")
    email          = Column(String(200), unique=True, nullable=False, index=True)
    password_hash  = Column(String(200), nullable=False)
    org_id         = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    role           = Column(String(20), default="editor")   # admin | editor | viewer
    is_active      = Column(Boolean, default=True)
    is_superadmin  = Column(Boolean, default=False)          # acceso a panel superadmin
    created_at     = Column(DateTime, default=datetime.utcnow)

    organization  = relationship("Organization", back_populates="users")


# =============================================================================
# PIPELINES
# =============================================================================

class Pipeline(Base):
    __tablename__ = "pipelines"

    pipeline_id  = Column(Integer, primary_key=True, index=True)
    pipeline     = Column(String(200), nullable=False)          # nombre
    description  = Column(Text, default="")
    config_json  = Column(Text, default="{}")                   # JSON del pipeline
    hidden       = Column(Boolean, default=False)
    last_run     = Column(DateTime, nullable=True)
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    organization = relationship("Organization", back_populates="pipelines")


# =============================================================================
# SPECS (plantillas de reportes)
# =============================================================================

class Spec(Base):
    __tablename__ = "specs"

    id_spec      = Column(Integer, primary_key=True, index=True)
    name         = Column(String(200), nullable=False)
    type         = Column(String(50), default="Evaluación")  # Evaluación | Gráficos | Tablas | Dashboard
    metadata_    = Column("metadata", Text, default="{}")    # JSON
    charts_list  = Column(Text, default="[]")                # JSON
    tables_list  = Column(Text, default="[]")                # JSON
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    organization = relationship("Organization", back_populates="specs")


# =============================================================================
# DIMENSIONS
# =============================================================================

class Dimension(Base):
    __tablename__ = "dimensions"

    id_dimension     = Column(Integer, primary_key=True, index=True)
    name             = Column(String(200), nullable=False)
    data_type        = Column(String(20), default="str")       # str | int | float
    validation_mode  = Column(String(20), default="free")      # free | list
    description      = Column(Text, default="")
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    organization     = relationship("Organization", back_populates="dimensions")
    values           = relationship("DimensionValue", back_populates="dimension", cascade="all, delete-orphan")
    metric_links     = relationship("MetricDimension", back_populates="dimension")


class DimensionValue(Base):
    __tablename__ = "dimension_values"

    id_value     = Column(Integer, primary_key=True, index=True)
    id_dimension = Column(Integer, ForeignKey("dimensions.id_dimension", ondelete="CASCADE"), nullable=False, index=True)
    value        = Column(String(200), nullable=False)
    is_active    = Column(Boolean, default=True)

    dimension    = relationship("Dimension", back_populates="values")


# =============================================================================
# METRICS
# =============================================================================

class Metric(Base):
    __tablename__ = "metrics"

    id_metric    = Column(Integer, primary_key=True, index=True)
    name         = Column(String(200), nullable=False)
    data_type    = Column(String(20), default="float")   # float | int | str | object
    meta_json    = Column(Text, default="{}")            # JSON: {"fields": [...]}
    description  = Column(Text, default="")
    unit         = Column(String(50), default="")
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    organization    = relationship("Organization", back_populates="metrics")
    dimension_links = relationship("MetricDimension", back_populates="metric", cascade="all, delete-orphan")
    data_points     = relationship("MetricData", back_populates="metric", cascade="all, delete-orphan")
    indicator_links = relationship("IndicatorMetric", back_populates="metric")


class MetricDimension(Base):
    """Tabla junction Metric ↔ Dimension (M-N)."""
    __tablename__ = "metric_dimensions"
    __table_args__ = (UniqueConstraint("id_metric", "id_dimension"),)

    id           = Column(Integer, primary_key=True, index=True)
    id_metric    = Column(Integer, ForeignKey("metrics.id_metric", ondelete="CASCADE"), nullable=False)
    id_dimension = Column(Integer, ForeignKey("dimensions.id_dimension", ondelete="CASCADE"), nullable=False)

    metric    = relationship("Metric", back_populates="dimension_links")
    dimension = relationship("Dimension", back_populates="metric_links")


class MetricData(Base):
    """Datos guardados para una métrica (filas de valores con dimensiones en JSON)."""
    __tablename__ = "metric_data"

    id_data         = Column(Integer, primary_key=True, index=True)
    id_metric       = Column(Integer, ForeignKey("metrics.id_metric", ondelete="CASCADE"), nullable=False, index=True)
    value           = Column(Text, nullable=True)        # puede ser float, int, str, o JSON serializado
    dimensions_json = Column(Text, default="{}")         # {"id_dimension": "valor", ...}
    created_at      = Column(DateTime, default=datetime.utcnow)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    metric = relationship("Metric", back_populates="data_points")


# =============================================================================
# INDICATORS
# =============================================================================

class Indicator(Base):
    __tablename__ = "indicators"

    id_indicator      = Column(Integer, primary_key=True, index=True)
    name              = Column(String(200), nullable=False)
    description       = Column(Text, default="")
    type              = Column(String(50), default="Evaluación")  # Evaluación | Estudio | Alerta
    column_roles      = Column(Text, default="{}")    # JSON
    role_labels       = Column(Text, default="{}")    # JSON
    role_formats      = Column(Text, default="{}")    # JSON
    filter_dimensions = Column(Text, default="[]")    # JSON array de ids
    temporal_config   = Column(Text, default="{}")    # JSON
    achievement_levels = Column(Text, default="[]")   # JSON array de strings
    dashboard_layout  = Column(Text, default="{}")    # JSON
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    org_id            = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    organization    = relationship("Organization", back_populates="indicators")
    metric_links    = relationship("IndicatorMetric", back_populates="indicator", cascade="all, delete-orphan")


class IndicatorMetric(Base):
    """Tabla junction Indicator ↔ Metric (M-N)."""
    __tablename__ = "indicator_metrics"
    __table_args__ = (UniqueConstraint("id_indicator", "id_metric"),)

    id           = Column(Integer, primary_key=True, index=True)
    id_indicator = Column(Integer, ForeignKey("indicators.id_indicator", ondelete="CASCADE"), nullable=False)
    id_metric    = Column(Integer, ForeignKey("metrics.id_metric", ondelete="CASCADE"), nullable=False)

    indicator = relationship("Indicator", back_populates="metric_links")
    metric    = relationship("Metric", back_populates="indicator_links")
