import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_

from apps.api.core.deps import get_db, get_current_user
from apps.api.models import DashboardLayout, User, Role
from apps.api.core.deps import get_current_user

router = APIRouter(prefix="/api/dashboard/layout", tags=["dashboard_layout"])

def migrate_layout_if_needed(layout_data: Any) -> Dict[str, Any]:
    if isinstance(layout_data, list):
        # Legacy PR-21 format: list of widgets
        # Convert to grid format
        widgets = []
        lg_layout = []
        for i, w in enumerate(layout_data):
            size = w.get("size", "medium")
            # Map size to cols (12 col grid)
            w_units = {"small": 3, "medium": 6, "large": 9, "full": 12}.get(size, 6)
            h_units = 2 if size in ["small", "medium"] else 3
            lg_layout.append({
                "i": w.get("id"),
                "x": (i * 4) % 12,
                "y": (i // 3) * 2,
                "w": w_units,
                "h": h_units
            })
            widgets.append(w)
        return {
            "widgets": widgets,
            "layouts": {"lg": lg_layout}
        }
    return layout_data or {"widgets": [], "layouts": {}}


@router.get("/")
def get_layout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get the dashboard layout for the current user.
    Fallbacks: User layout -> Tenant Default -> System Default (Hardcoded in frontend).
    """
    # Try user layout first
    layout_model = db.execute(
        select(DashboardLayout).where(
            and_(
                DashboardLayout.tenant_id == current_user.tenant_id,
                DashboardLayout.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()

    if layout_model:
        return {"layout": migrate_layout_if_needed(layout_model.layout), "is_default": False}

    # Fallback to tenant default
    default_model = db.execute(
        select(DashboardLayout).where(
            and_(
                DashboardLayout.tenant_id == current_user.tenant_id,
                DashboardLayout.is_default == True
            )
        )
    ).scalar_one_or_none()

    if default_model:
        return {"layout": migrate_layout_if_needed(default_model.layout), "is_default": True}

    # No layout found, return empty (frontend will inject system default)
    return {"layout": None, "is_default": True}


@router.put("/")
def save_layout(layout: List[Dict[str, Any]], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Save the personalized layout for the current user.
    """
    layout_model = db.execute(
        select(DashboardLayout).where(
            and_(
                DashboardLayout.tenant_id == current_user.tenant_id,
                DashboardLayout.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()

    if layout_model:
        layout_model.layout = layout
    else:
        layout_model = DashboardLayout(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            layout=layout,
            is_default=False
        )
        db.add(layout_model)

    db.commit()
    return {"status": "success", "layout": layout_model.layout}


@router.post("/tenant-default")
def publish_tenant_default(layout: List[Dict[str, Any]], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Publish a layout as the tenant-wide default. Only Admins/Owners.
    """
    if current_user.role not in [Role.admin, Role.owner]:
        raise HTTPException(status_code=403, detail="Only admins or owners can publish tenant default layouts.")

    default_model = db.execute(
        select(DashboardLayout).where(
            and_(
                DashboardLayout.tenant_id == current_user.tenant_id,
                DashboardLayout.is_default == True
            )
        )
    ).scalar_one_or_none()

    if default_model:
        default_model.layout = layout
    else:
        default_model = DashboardLayout(
            tenant_id=current_user.tenant_id,
            user_id=None,
            layout=layout,
            is_default=True
        )
        db.add(default_model)

    db.commit()
    return {"status": "success", "layout": default_model.layout}


@router.delete("/")
def reset_to_default(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Reset user's layout back to tenant default/system default.
    """
    layout_model = db.execute(
        select(DashboardLayout).where(
            and_(
                DashboardLayout.tenant_id == current_user.tenant_id,
                DashboardLayout.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()

    if layout_model:
        db.delete(layout_model)
        db.commit()

    return {"status": "success"}
