import unittest

from fastapi import HTTPException

from app.models import Department, Task, User
from app.routes.tasks import can_manage_task, scoped_task_query
from app.utils.auth import get_department_head_department_id


class DepartmentHeadAuthorizationTests(unittest.TestCase):
    def make_user(self, role="DEPARTMENT_HEAD", department_name="Housekeeping", department_resort_id=1):
        department = Department(id=10, resort_id=department_resort_id, name=department_name)
        user = User(
            id=20,
            resort_id=1,
            department_id=10,
            role=role,
            department=department,
        )
        return user

    def test_all_four_operational_departments_are_allowed(self):
        for department_name in ("Housekeeping", "Maintenance", "Food & Beverage", "Inventory"):
            with self.subTest(department=department_name):
                user = self.make_user(department_name=department_name)
                self.assertEqual(get_department_head_department_id(user), 10)

    def test_front_desk_and_unknown_departments_are_rejected(self):
        for department_name in ("Front Desk", "Sales"):
            with self.subTest(department=department_name):
                with self.assertRaises(HTTPException) as raised:
                    get_department_head_department_id(self.make_user(department_name=department_name))
                self.assertEqual(raised.exception.status_code, 403)

    def test_user_must_be_a_head_of_a_department_in_their_resort(self):
        for user in (
            self.make_user(role="MANAGER"),
            self.make_user(department_resort_id=2),
        ):
            with self.subTest(user=user):
                with self.assertRaises(HTTPException) as raised:
                    get_department_head_department_id(user)
                self.assertEqual(raised.exception.status_code, 403)

    def test_task_query_and_mutations_stay_in_the_head_department(self):
        user = self.make_user(department_name="Inventory")

        class QueryRecorder:
            def __init__(self):
                self.filters = []

            def filter(self, condition):
                self.filters.append(condition)
                return self

        query = scoped_task_query(QueryRecorder(), user)
        compiled_filter = query.filters[0].compile()
        self.assertIn(10, compiled_filter.params.values())
        self.assertTrue(can_manage_task(Task(department_id=10), user))
        self.assertFalse(can_manage_task(Task(department_id=11), user))


if __name__ == "__main__":
    unittest.main()