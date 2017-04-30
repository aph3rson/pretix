from datetime import timedelta

import pytest
from django.utils.timezone import now

from pretix.base.models import Event, Order, Organizer, Team, User


@pytest.fixture
def env():
    o = Organizer.objects.create(name='Dummy', slug='dummy')
    event = Event.objects.create(
        organizer=o, name='Dummy', slug='dummy',
        date_from=now(), plugins='pretix.plugins.banktransfer'
    )
    user = User.objects.create_user('dummy@dummy.dummy', 'dummy')
    Order.objects.create(
        code='FOO', event=event,
        status=Order.STATUS_PENDING,
        datetime=now(), expires=now() + timedelta(days=10),
        total=0, payment_provider='banktransfer'
    )
    return event, user, o

superuser_urls = [
    "global/settings/",
    "global/update/",
]

event_urls = [
    "",
    "settings/",
    "settings/plugins",
    "settings/payment",
    "settings/tickets",
    "settings/permissions",
    "settings/email",
    "settings/invoice",
    "settings/invoice/preview",
    "settings/display",
    "items/",
    "items/add",
    "items/1/",
    "items/1/variations",
    "items/1/up",
    "items/1/down",
    "items/1/delete",
    "categories/",
    "categories/add",
    "categories/2/",
    "categories/2/up",
    "categories/2/down",
    "categories/2/delete",
    "questions/",
    "questions/2/delete",
    "questions/2/",
    "questions/add",
    "vouchers/",
    "vouchers/2/delete",
    "vouchers/2/",
    "vouchers/add",
    "vouchers/bulk_add",
    "vouchers/rng",
    "quotas/",
    "quotas/2/delete",
    "quotas/2/change",
    "quotas/2/",
    "quotas/add",
    "orders/ABC/transition",
    "orders/ABC/resend",
    "orders/ABC/invoice",
    "orders/ABC/extend",
    "orders/ABC/change",
    "orders/ABC/contact",
    "orders/ABC/comment",
    "orders/ABC/locale",
    "orders/ABC/",
    "orders/",
    "waitinglist/",
    "waitinglist/auto_assign",
    "invoice/1",
]

organizer_urls = [
    'organizer/abc/edit',
    'organizer/abc/',
    'organizer/abc/teams',
    'organizer/abc/team/1/',
    'organizer/abc/team/1/edit',
    'organizer/abc/team/1/delete',
    'organizer/abc/team/add',
]


@pytest.fixture
def perf_patch(monkeypatch):
    # Patch out template rendering for performance improvements
    monkeypatch.setattr("django.template.backends.django.Template.render", lambda *args, **kwargs: "mocked template")


@pytest.mark.django_db
@pytest.mark.parametrize("url", [
    "",
    "settings",
    "admin/",
    "organizers/",
    "organizers/add",
    "events/",
    "events/add",
] + ['event/dummy/dummy/' + u for u in event_urls] + organizer_urls)
def test_logged_out(client, env, url):
    client.logout()
    response = client.get('/control/' + url)
    assert response.status_code == 302
    assert "/control/login" in response['Location']


@pytest.mark.django_db
@pytest.mark.parametrize("url", superuser_urls)
def test_superuser_required(perf_patch, client, env, url):
    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/' + url)
    assert response.status_code == 403
    env[1].is_superuser = True
    env[1].save()
    response = client.get('/control/' + url)
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("url", event_urls)
def test_wrong_event(perf_patch, client, env, url):
    event2 = Event.objects.create(
        organizer=env[2], name='Dummy', slug='dummy2',
        date_from=now(), plugins='pretix.plugins.banktransfer'
    )
    t = Team.objects.create(organizer=env[2], can_change_event_settings=True)
    t.members.add(env[1])
    t.limit_events.add(event2)

    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/event/dummy/dummy/' + url)
    # These permission violations do not yield a 403 error, but
    # a 404 error to prevent information leakage
    assert response.status_code == 404


event_permission_urls = [
    ("can_change_event_settings", "live/", 200),
    ("can_change_event_settings", "settings/", 200),
    ("can_change_event_settings", "settings/plugins", 200),
    ("can_change_event_settings", "settings/payment", 200),
    ("can_change_event_settings", "settings/tickets", 200),
    ("can_change_event_settings", "settings/email", 200),
    ("can_change_event_settings", "settings/display", 200),
    ("can_change_event_settings", "settings/invoice", 200),
    ("can_change_event_settings", "settings/invoice/preview", 200),
    # Lists are currently not access-controlled
    # ("can_change_items", "items/", 200),
    ("can_change_items", "items/add", 200),
    ("can_change_items", "items/1/up", 404),
    ("can_change_items", "items/1/down", 404),
    ("can_change_items", "items/1/delete", 404),
    # ("can_change_items", "categories/", 200),
    # We don't have to create categories and similar objects
    # for testing this, it is enough to test that a 404 error
    # is returned instead of a 403 one.
    ("can_change_items", "categories/2/", 404),
    ("can_change_items", "categories/2/delete", 404),
    ("can_change_items", "categories/2/up", 404),
    ("can_change_items", "categories/2/down", 404),
    ("can_change_items", "categories/add", 200),
    # ("can_change_items", "questions/", 200),
    ("can_change_items", "questions/2/", 404),
    ("can_change_items", "questions/2/delete", 404),
    ("can_change_items", "questions/add", 200),
    # ("can_change_items", "quotas/", 200),
    ("can_change_items", "quotas/2/change", 404),
    ("can_change_items", "quotas/2/delete", 404),
    ("can_change_items", "quotas/add", 200),
    ("can_view_orders", "orders/overview/", 200),
    ("can_view_orders", "orders/export/", 200),
    ("can_view_orders", "orders/", 200),
    ("can_view_orders", "orders/FOO/", 200),
    ("can_change_orders", "orders/FOO/extend", 200),
    ("can_change_orders", "orders/FOO/contact", 200),
    ("can_change_orders", "orders/FOO/transition", 405),
    ("can_change_orders", "orders/FOO/resend", 405),
    ("can_change_orders", "orders/FOO/invoice", 405),
    ("can_change_orders", "orders/FOO/change", 200),
    ("can_change_orders", "orders/FOO/comment", 405),
    ("can_change_orders", "orders/FOO/locale", 200),
    ("can_change_vouchers", "vouchers/add", 200),
    ("can_change_orders", "requiredactions/", 200),
    ("can_change_vouchers", "vouchers/bulk_add", 200),
    ("can_view_vouchers", "vouchers/", 200),
    ("can_view_vouchers", "vouchers/tags/", 200),
    ("can_change_vouchers", "vouchers/1234/", 404),
    ("can_change_vouchers", "vouchers/1234/delete", 404),
    ("can_view_orders", "waitinglist/", 200),
    ("can_change_orders", "waitinglist/auto_assign", 405),
]


@pytest.mark.django_db
@pytest.mark.parametrize("perm,url,code", event_permission_urls)
def test_wrong_event_permission(perf_patch, client, env, perm, url, code):
    t = Team(
        organizer=env[2], all_events=True
    )
    setattr(t, perm, False)
    t.save()
    t.members.add(env[1])
    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/event/dummy/dummy/' + url)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("perm,url,code", event_permission_urls)
def test_limited_event_permission_for_other_event(perf_patch, client, env, perm, url, code):
    event2 = Event.objects.create(
        organizer=env[2], name='Dummy', slug='dummy2',
        date_from=now(), plugins='pretix.plugins.banktransfer'
    )
    t = Team.objects.create(organizer=env[2], can_change_event_settings=True)
    t.members.add(env[1])
    t.limit_events.add(event2)

    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/event/dummy/dummy/' + url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_current_permission(client, env):
    t = Team(
        organizer=env[2], all_events=True
    )
    setattr(t, 'can_change_event_settings', True)
    t.save()
    t.members.add(env[1])

    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/event/dummy/dummy/settings/')
    assert response.status_code == 200
    setattr(t, 'can_change_event_settings', False)
    t.save()
    response = client.get('/control/event/dummy/dummy/settings/')
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("perm,url,code", event_permission_urls)
def test_correct_event_permission_all_events(perf_patch, client, env, perm, url, code):
    t = Team(organizer=env[2], all_events=True)
    setattr(t, perm, True)
    t.save()
    t.members.add(env[1])
    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/event/dummy/dummy/' + url)
    assert response.status_code == code


@pytest.mark.django_db
@pytest.mark.parametrize("perm,url,code", event_permission_urls)
def test_correct_event_permission_limited(perf_patch, client, env, perm, url, code):
    t = Team(organizer=env[2])
    setattr(t, perm, True)
    t.save()
    t.members.add(env[1])
    t.limit_events.add(env[0])
    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/event/dummy/dummy/' + url)
    assert response.status_code == code


@pytest.mark.django_db
@pytest.mark.parametrize("url", organizer_urls)
def test_wrong_organizer(perf_patch, client, env, url):
    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/' + url)
    # These permission violations do not yield a 403 error, but
    # a 404 error to prevent information leakage
    assert response.status_code == 404


organizer_permission_urls = [
    ("can_change_teams", "organizer/dummy/teams", 200),
    ("can_change_teams", "organizer/dummy/team/add", 200),
    ("can_change_teams", "organizer/dummy/team/1/", 200),
    ("can_change_teams", "organizer/dummy/team/1/edit", 200),
    ("can_change_teams", "organizer/dummy/team/1/delete", 200),
    ("can_change_organizer_settings", "organizer/dummy/edit", 200),
]


@pytest.mark.django_db
@pytest.mark.parametrize("perm,url,code", organizer_permission_urls)
def test_wrong_organizer_permission(perf_patch, client, env, perm, url, code):
    t = Team(organizer=env[2])
    setattr(t, perm, False)
    t.save()
    t.members.add(env[1])
    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/' + url)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("perm,url,code", organizer_permission_urls)
def test_correct_organizer_permission(perf_patch, client, env, perm, url, code):
    t = Team(organizer=env[2])
    setattr(t, perm, True)
    t.save()
    t.members.add(env[1])
    client.login(email='dummy@dummy.dummy', password='dummy')
    response = client.get('/control/' + url)
    assert response.status_code == code
