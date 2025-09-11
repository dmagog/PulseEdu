"""
Role-Based Access Control (RBAC) service.
"""

import logging
from typing import Dict, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.user import Role, User, UserRole

logger = logging.getLogger("app.rbac")


class RBACService:
    """Service for managing role-based access control."""

    # Define role permissions
    ROLE_PERMISSIONS = {
        "admin": {
            "admin.settings": ["read", "write"],
            "admin.metrics": ["read"],
            "admin.users": ["read", "write"],
            "admin.staff": ["read", "write"],
            "admin.students": ["read", "write"],
            "admin.courses": ["read", "write"],
            "import.upload": ["read", "write"],
            "import.jobs": ["read", "write"],
            "student.view": ["read"],
            "teacher.view": ["read"],
            "rop.view": ["read"],
            "system.manage": ["read", "write"],
            "system.status": ["read"],
        },
        "operator": {"import.upload": ["read", "write"], "import.jobs": ["read", "write"], "student.view": ["read"]},
        "teacher": {
            "teacher.view": ["read"],
            "teacher.courses": ["read", "write"],
            "teacher.students": ["read"],
            "teacher.analytics": ["read"],
            "teacher.schedule": ["read", "write"],
            "student.view": ["read"],
        },
        "rop": {
            "rop.view": ["read"],
            "rop.programs": ["read", "write"],
            "rop.trends": ["read"],
            "rop.quality": ["read", "write"],
            "teacher.view": ["read"],
            "student.view": ["read"],
        },
        "student": {
            "student.view": ["read"],
            "student.courses": ["read"],
            "student.progress": ["read"],
            "student.assignments": ["read"],
            "student.schedule": ["read"],
            "student.recommendations": ["read"],
        },
    }

    def __init__(self):
        self.logger = logger

    def get_user_roles(self, user_id: str, db: Session) -> List[str]:
        """
        Get all roles for a user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            List of role names
        """
        try:
            user_roles = db.query(UserRole).join(Role).filter(UserRole.user_id == user_id).all()

            roles = [user_role.role.role_name for user_role in user_roles]
            self.logger.debug(f"User {user_id} has roles: {roles}")

            return roles

        except Exception as e:
            self.logger.error(f"Error getting user roles: {e}")
            return []

    def has_permission(self, user_id: str, resource: str, action: str, db: Session) -> bool:
        """
        Check if user has permission to perform action on resource.

        Args:
            user_id: User ID
            resource: Resource name (e.g., "admin.settings", "import.upload")
            action: Action name (e.g., "read", "write")
            db: Database session

        Returns:
            True if user has permission, False otherwise
        """
        try:
            user_roles = self.get_user_roles(user_id, db)

            # Check if any role has the required permission
            for role in user_roles:
                if self._role_has_permission(role, resource, action):
                    self.logger.debug(f"User {user_id} has permission {action} on {resource} via role {role}")
                    return True

            self.logger.warning(f"User {user_id} denied access to {action} on {resource}")
            return False

        except Exception as e:
            self.logger.error(f"Error checking permission: {e}")
            return False

    def _role_has_permission(self, role: str, resource: str, action: str) -> bool:
        """
        Check if role has specific permission.

        Args:
            role: Role name
            resource: Resource name
            action: Action name

        Returns:
            True if role has permission, False otherwise
        """
        role_permissions = self.ROLE_PERMISSIONS.get(role, {})
        resource_permissions = role_permissions.get(resource, [])

        return action in resource_permissions

    def get_accessible_resources(self, user_id: str, db: Session) -> Dict[str, List[str]]:
        """
        Get all resources and actions accessible to user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dictionary mapping resources to list of allowed actions
        """
        try:
            user_roles = self.get_user_roles(user_id, db)
            accessible = {}

            for role in user_roles:
                role_permissions = self.ROLE_PERMISSIONS.get(role, {})
                for resource, actions in role_permissions.items():
                    if resource not in accessible:
                        accessible[resource] = set()
                    accessible[resource].update(actions)

            # Convert sets to lists
            return {resource: list(actions) for resource, actions in accessible.items()}

        except Exception as e:
            self.logger.error(f"Error getting accessible resources: {e}")
            return {}

    def assign_role_to_user(self, user_id: str, role_name: str, db: Session) -> bool:
        """
        Assign role to user.

        Args:
            user_id: User ID
            role_name: Role name
            db: Database session

        Returns:
            True if role assigned successfully, False otherwise
        """
        try:
            # Check if role exists
            role = db.query(Role).filter(Role.role_name == role_name).first()
            if not role:
                self.logger.error(f"Role {role_name} not found")
                return False

            # Check if user already has this role
            existing = db.query(UserRole).filter(and_(UserRole.user_id == user_id, UserRole.role_id == role.role_id)).first()

            if existing:
                self.logger.info(f"User {user_id} already has role {role_name}")
                return True

            # Assign role
            user_role = UserRole(user_id=user_id, role_id=role.role_id)
            db.add(user_role)
            db.commit()

            self.logger.info(f"Assigned role {role_name} to user {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error assigning role: {e}")
            db.rollback()
            return False

    def remove_role_from_user(self, user_id: str, role_name: str, db: Session) -> bool:
        """
        Remove role from user.

        Args:
            user_id: User ID
            role_name: Role name
            db: Database session

        Returns:
            True if role removed successfully, False otherwise
        """
        try:
            # Find role
            role = db.query(Role).filter(Role.role_name == role_name).first()
            if not role:
                self.logger.error(f"Role {role_name} not found")
                return False

            # Remove user role
            user_role = db.query(UserRole).filter(and_(UserRole.user_id == user_id, UserRole.role_id == role.role_id)).first()

            if user_role:
                db.delete(user_role)
                db.commit()
                self.logger.info(f"Removed role {role_name} from user {user_id}")
                return True
            else:
                self.logger.info(f"User {user_id} doesn't have role {role_name}")
                return True

        except Exception as e:
            self.logger.error(f"Error removing role: {e}")
            db.rollback()
            return False

    def get_users_by_role(self, role_name: str, db: Session) -> List[User]:
        """
        Get all users with specific role.

        Args:
            role_name: Role name
            db: Database session

        Returns:
            List of users with the role
        """
        try:
            users = db.query(User).join(UserRole).join(Role).filter(Role.role_name == role_name).all()

            return users

        except Exception as e:
            self.logger.error(f"Error getting users by role: {e}")
            return []

    def is_admin(self, user_id: str, db: Session) -> bool:
        """Check if user is admin."""
        return self.has_permission(user_id, "system.manage", "write", db)

    def is_operator(self, user_id: str, db: Session) -> bool:
        """Check if user is operator."""
        return self.has_permission(user_id, "import.upload", "write", db)

    def is_student(self, user_id: str, db: Session) -> bool:
        """Check if user is student."""
        return self.has_permission(user_id, "student.view", "read", db)
