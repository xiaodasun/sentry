from __future__ import absolute_import

from datetime import timedelta
from django.utils import timezone

from sentry.api.paginator import (Paginator, DateTimePaginator, OffsetPaginator)
from sentry.models import User
from sentry.testutils import TestCase


class PaginatorTest(TestCase):
    cls = Paginator

    def test_max_limit(self):
        self.create_user('foo@example.com')
        self.create_user('bar@example.com')
        self.create_user('baz@example.com')

        queryset = User.objects.all()

        paginator = self.cls(queryset, 'id', max_limit=10)
        result = paginator.get_result(limit=2, cursor=None)
        assert len(result) == 2

        paginator = self.cls(queryset, 'id', max_limit=1)
        result = paginator.get_result(limit=2, cursor=None)
        assert len(result) == 1

    def test_count_hits(self):
        self.create_user('foo@example.com')
        self.create_user('bar@example.com')

        queryset = User.objects.filter(email='foo@example.com')
        paginator = self.cls(queryset, 'id')
        result = paginator.count_hits(1000)
        assert result == 1

        queryset = User.objects.all()
        paginator = self.cls(queryset, 'id')
        result = paginator.count_hits(1000)
        assert result == 2

        queryset = User.objects.none()
        paginator = self.cls(queryset, 'id')
        result = paginator.count_hits(1000)
        assert result == 0

        queryset = User.objects.all()
        paginator = self.cls(queryset, 'id')
        result = paginator.count_hits(1)
        assert result == 1

    def test_prev_emptyset(self):
        queryset = User.objects.all()

        paginator = self.cls(queryset, 'id')
        result1 = paginator.get_result(limit=1, cursor=None)

        res1 = self.create_user('foo@example.com')

        result2 = paginator.get_result(limit=1, cursor=result1.prev)
        assert len(result2) == 1, (result2, list(result2))
        assert result2[0] == res1

        result3 = paginator.get_result(limit=1, cursor=result2.prev)
        assert len(result3) == 0, (result3, list(result3))


class OffsetPaginatorTest(TestCase):
    # offset paginator does not support dynamic limits on is_prev
    def test_simple(self):
        res1 = self.create_user('foo@example.com')
        res2 = self.create_user('bar@example.com')
        res3 = self.create_user('baz@example.com')

        queryset = User.objects.all()

        paginator = OffsetPaginator(queryset, 'id')
        result1 = paginator.get_result(limit=1, cursor=None)
        assert len(result1) == 1, result1
        assert result1[0] == res1
        assert result1.next
        assert not result1.prev

        result2 = paginator.get_result(limit=1, cursor=result1.next)
        assert len(result2) == 1, (result2, list(result2))
        assert result2[0] == res2
        assert result2.next
        assert result2.prev

        result3 = paginator.get_result(limit=1, cursor=result2.next)
        assert len(result3) == 1, result3
        assert result3[0] == res3
        assert not result3.next
        assert result3.prev

        result4 = paginator.get_result(limit=1, cursor=result3.next)
        assert len(result4) == 0, result4
        assert not result4.next
        assert result4.prev

        result5 = paginator.get_result(limit=1, cursor=result4.prev)
        assert len(result5) == 1, result5
        assert result5[0] == res3
        assert not result5.next
        assert result5.prev


class DateTimePaginatorTest(TestCase):
    def test_ascending(self):
        joined = timezone.now()

        # The DateTime pager only has accuracy up to 1000th of a second.
        # Everythng can't be added within less than a ms of each other as the
        # pager will fail.
        #
        # TODO(epurkhiser): Decided if the date time pager needs tihs accuracy
        res1 = self.create_user('foo@example.com', date_joined=joined)
        res2 = self.create_user('bar@example.com', date_joined=joined + timedelta(seconds=1))
        res3 = self.create_user('baz@example.com', date_joined=joined + timedelta(seconds=2))
        res4 = self.create_user('qux@example.com', date_joined=joined + timedelta(seconds=3))

        queryset = User.objects.all()

        paginator = DateTimePaginator(queryset, 'date_joined')
        result1 = paginator.get_result(limit=2, cursor=None)
        assert len(result1) == 2, result1
        assert result1[0] == res1
        assert result1[1] == res2
        assert result1.next
        assert not result1.prev

        result2 = paginator.get_result(limit=2, cursor=result1.next)
        assert len(result2) == 2, result2
        assert result2[0] == res3
        assert result2[1] == res4
        assert not result2.next
        assert result2.prev

        result3 = paginator.get_result(limit=1, cursor=result2.prev)
        assert len(result3) == 1, result3
        assert result3[0] == res2
        assert result3.next
        assert result3.prev

        result4 = paginator.get_result(limit=1, cursor=result3.prev)
        assert len(result4) == 1, result4
        assert result4[0] == res1
        assert result4.next
        assert not result4.prev

    def test_descending(self):
        joined = timezone.now()

        res1 = self.create_user('foo@example.com', date_joined=joined)
        res2 = self.create_user('bar@example.com', date_joined=joined + timedelta(seconds=1))
        res3 = self.create_user('baz@example.com', date_joined=joined + timedelta(seconds=2))

        queryset = User.objects.all()

        paginator = DateTimePaginator(queryset, '-date_joined')
        result1 = paginator.get_result(limit=1, cursor=None)
        assert len(result1) == 1, result1
        assert result1[0] == res3
        assert result1.next
        assert not result1.prev

        result2 = paginator.get_result(limit=2, cursor=result1.next)
        assert len(result2) == 2, result2
        assert result2[0] == res2
        assert result2[1] == res1
        assert not result2.next
        assert result2.prev

        result3 = paginator.get_result(limit=2, cursor=result2.prev)
        assert len(result3) == 1, result3
        assert result3[0] == res3
        assert result3.next
        assert not result3.prev

    def test_prev_descending_with_new(self):
        joined = timezone.now()

        res1 = self.create_user('foo@example.com', date_joined=joined)
        res2 = self.create_user('bar@example.com', date_joined=joined + timedelta(seconds=1))

        queryset = User.objects.all()

        paginator = DateTimePaginator(queryset, '-date_joined')
        result1 = paginator.get_result(limit=10, cursor=None)
        assert len(result1) == 2, result1
        assert result1[0] == res2
        assert result1[1] == res1

        res3 = self.create_user('baz@example.com', date_joined=joined + timedelta(seconds=2))
        res4 = self.create_user('qux@example.com', date_joined=joined + timedelta(seconds=3))

        result2 = paginator.get_result(limit=10, cursor=result1.prev)
        assert len(result2) == 2, result2
        assert result2[0] == res4
        assert result2[1] == res3

        result3 = paginator.get_result(limit=10, cursor=result2.prev)
        assert len(result3) == 0, result3

        result4 = paginator.get_result(limit=10, cursor=result1.next)
        assert len(result4) == 0, result4

    def test_rounding_precision(self):
        joined = timezone.now()

        res1 = self.create_user('foo@example.com', date_joined=joined)
        res2 = self.create_user('bar@example.com', date_joined=joined + timedelta(microseconds=1))
        res3 = self.create_user('baz@example.com', date_joined=joined + timedelta(microseconds=2))
        res4 = self.create_user('qux@example.com', date_joined=joined + timedelta(microseconds=3))

        queryset = User.objects.all()

        paginator = DateTimePaginator(queryset, 'date_joined')
        result1 = paginator.get_result(limit=3, cursor=None)
        assert len(result1) == 3, result1
        assert result1[0] == res1
        assert result1[1] == res2
        assert result1[2] == res3

        result2 = paginator.get_result(limit=10, cursor=result1.next)
        assert len(result2) == 1, result2
        assert result2[0] == res4

        result3 = paginator.get_result(limit=2, cursor=result2.prev)
        assert len(result3) == 2, result3
        assert result3[0] == res2
        assert result3[1] == res3

        result4 = paginator.get_result(limit=1, cursor=result3.prev)
        assert len(result4) == 1, result4
        assert result4[0] == res1

        result5 = paginator.get_result(limit=10, cursor=result4.prev)
        assert len(result5) == 0, list(result5)
