import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from datetime import timedelta

from django.utils import timezone

from .models import (
    ADMIN_FULLNAME, ADMIN_STUDENT_ID, Account, ActivityLog, ChatMessage, ConcernReply,
    PrivateMessage, StudentConcern,
)

CCS = 'College of Computer Studies'
EDU = 'College of Education'


def image_file(name='proof.png', fmt='PNG'):
    buffer = io.BytesIO()
    Image.new('RGB', (20, 20), 'yellow').save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RoleTests(TestCase):
    def setUp(self):
        self.student = Account.objects.create(role='student', Fullname='Juan Cruz', StudentID=1001, College=CCS)
        self.other = Account.objects.create(role='student', Fullname='Maria Lopez', StudentID=1002, College=EDU)
        self.staff = Account.objects.create(role='staff', Fullname='Ana Reyes', College=CCS)
        self.admin = Account.objects.create(role='admin', Fullname=ADMIN_FULLNAME, StudentID=ADMIN_STUDENT_ID)
        self.mine = StudentConcern.objects.create(
            author=self.student, Fullname='Juan Cruz', StudentID=1001, College=CCS, Concern='Broken aircon in lab')
        self.theirs = StudentConcern.objects.create(
            author=self.other, Fullname='Maria Lopez', StudentID=1002, College=EDU, Concern='Library hours too short')

    def login(self, **data):
        return self.client.post(reverse('login'), data)

    def as_student(self):
        self.login(role='student', Fullname='juan cruz', StudentID=1001)

    def as_staff(self):
        self.login(role='staff', Fullname='Ana Reyes', College=CCS)

    def as_admin(self):
        self.login(role='admin', Fullname=ADMIN_FULLNAME, StudentID=ADMIN_STUDENT_ID)

    def test_login_required(self):
        self.assertEqual(self.client.get(reverse('StudentConcern')).status_code, 302)

    def test_logins(self):
        self.as_student()
        self.assertEqual(self.client.session['account_id'], self.student.pk)
        self.client.post(reverse('logout'))
        self.as_staff()
        self.assertEqual(self.client.session['account_id'], self.staff.pk)
        self.client.post(reverse('logout'))
        self.as_admin()
        self.assertEqual(self.client.session['account_id'], self.admin.pk)

    def test_bad_logins(self):
        self.login(role='student', Fullname='Juan Cruz', StudentID=9999)
        self.login(role='staff', Fullname='Ana Reyes', College=EDU)
        self.login(role='admin', Fullname='Juan Cruz', StudentID=1001)
        self.login(role='admin', Fullname=ADMIN_FULLNAME, StudentID=1)
        self.assertNotIn('account_id', self.client.session)
        self.assertEqual(ActivityLog.objects.filter(action='login_failed').count(), 4)

    def test_student_sees_anonymous_others(self):
        self.as_student()
        html = self.client.get(reverse('StudentConcern')).content.decode()
        self.assertIn('Juan Cruz', html)
        self.assertIn('Anonymous Participant', html)
        self.assertIn('College of ***', html)
        self.assertNotIn('Maria Lopez', html)
        self.assertNotIn('College of Education', html.split('<tbody>')[1])
        self.assertNotIn('1002', html)

    def test_student_search_cannot_leak_identity(self):
        self.as_student()
        for term in ('Maria', '1002', 'Education'):
            html = self.client.get(reverse('StudentConcern'), {'q': term}).content.decode()
            self.assertNotIn('Library hours', html)
        html = self.client.get(reverse('StudentConcern'), {'q': 'Library'}).content.decode()
        self.assertIn('Library hours', html)
        html = self.client.get(reverse('StudentConcern'), {'college': EDU}).content.decode()
        self.assertIn('Broken aircon', html)

    def test_student_detail_hides_identity(self):
        self.as_student()
        html = self.client.get(reverse('concern_detail', args=[self.theirs.pk])).content.decode()
        self.assertNotIn('Maria Lopez', html)
        self.assertNotIn('Update Status', html)

    def test_staff_sees_college_not_names(self):
        self.as_staff()
        html = self.client.get(reverse('StudentConcern')).content.decode()
        self.assertIn('College of Education', html)
        self.assertNotIn('Juan Cruz', html)
        self.assertNotIn('Maria Lopez', html)
        self.assertEqual(self.client.get(reverse('StudentConcern'), {'q': 'Maria'}).content.decode().count('Library hours'), 0)
        self.assertIn('Library hours', self.client.get(reverse('StudentConcern'), {'q': 'Education'}).content.decode())

    def test_staff_own_concern_shows_name(self):
        self.as_staff()
        self.client.post(reverse('concern_create'), {'category': 'Facilities', 'priority': 'High', 'Concern': 'Staff room leak'})
        html = self.client.get(reverse('StudentConcern')).content.decode()
        self.assertIn('Ana Reyes', html)

    def test_staff_status_and_reply(self):
        self.as_staff()
        self.client.post(reverse('concern_status', args=[self.mine.pk]), {'status': 'Resolved'})
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.status, 'Resolved')
        self.client.post(reverse('concern_reply', args=[self.mine.pk]), {'kind': 'Action Report', 'message': 'Aircon repaired'})
        self.assertEqual(ConcernReply.objects.get().kind, 'Action Report')
        self.assertTrue(ActivityLog.objects.filter(action='change_status').exists())

    def test_student_cannot_change_status_or_admin_pages(self):
        self.as_student()
        self.assertEqual(self.client.post(reverse('concern_status', args=[self.mine.pk]), {'status': 'Resolved'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('concern_reply', args=[self.mine.pk]), {'kind': 'Feedback', 'message': 'x'}).status_code, 403)
        for name in ('accounts_list', 'activity_logs', 'activity_feed', 'account_create', 'export_csv'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        for name in ('concern_update', 'concern_delete'):
            self.assertEqual(self.client.get(reverse(name, args=[self.mine.pk])).status_code, 403, name)

    def test_staff_blocked_from_admin_pages(self):
        self.as_staff()
        for name in ('accounts_list', 'activity_logs', 'account_create'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        self.assertEqual(self.client.get(reverse('concern_delete', args=[self.mine.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('export_csv')).status_code, 200)

    def test_submit_with_image(self):
        self.as_student()
        response = self.client.post(reverse('concern_create'), {
            'category': 'Facilities', 'priority': 'Urgent', 'Concern': 'Flooded hallway', 'evidence': image_file(),
        })
        self.assertEqual(response.status_code, 302)
        concern = StudentConcern.objects.get(Concern='Flooded hallway')
        self.assertTrue(concern.evidence.name.startswith('evidence/'))
        self.assertEqual(concern.College, CCS)
        self.assertEqual(concern.StudentID, 1001)
        html = self.client.get(reverse('concern_detail', args=[concern.pk])).content.decode()
        self.assertIn(concern.evidence.url, html)
        self.client.get(concern.evidence.url)

    def test_reject_non_image(self):
        self.as_student()
        bad = SimpleUploadedFile('x.png', b'not an image', content_type='image/png')
        response = self.client.post(reverse('concern_create'), {
            'category': 'Other', 'priority': 'Low', 'Concern': 'Bad upload', 'evidence': bad,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StudentConcern.objects.filter(Concern='Bad upload').exists())

    def test_admin_account_management(self):
        self.as_admin()
        response = self.client.post(reverse('account_create'), {
            'role': 'student', 'Fullname': 'New Student', 'StudentID': 2001, 'College': CCS})
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse('account_create'), {
            'role': 'student', 'Fullname': 'Dup', 'StudentID': 2001, 'College': CCS})
        self.assertEqual(response.status_code, 200)
        self.client.post(reverse('account_create'), {'role': 'staff', 'Fullname': 'New Staff', 'College': EDU})
        self.assertTrue(Account.objects.filter(role='staff', Fullname='New Staff', StudentID=None).exists())
        target = Account.objects.get(StudentID=2001)
        self.client.post(reverse('account_delete', args=[target.pk]))
        self.assertFalse(Account.objects.filter(pk=target.pk).exists())
        self.assertEqual(self.client.get(reverse('account_delete', args=[self.admin.pk])).status_code, 404)

    def test_deleted_account_loses_session(self):
        self.as_student()
        self.student.delete()
        self.assertEqual(self.client.get(reverse('StudentConcern')).status_code, 302)

    def test_admin_sees_everything_and_logs(self):
        self.as_student()
        self.client.get(reverse('StudentConcern'), {'q': 'aircon'})
        self.client.post(reverse('logout'))
        self.as_admin()
        html = self.client.get(reverse('StudentConcern')).content.decode()
        self.assertIn('Maria Lopez', html)
        self.assertIn('1002', html)
        logs = self.client.get(reverse('activity_logs')).content.decode()
        self.assertIn('1001', logs)
        self.assertIn('Searched', logs)
        feed = self.client.get(reverse('activity_feed'), {'after': 0}).json()
        self.assertTrue(feed['rows'])
        last = feed['last_id']
        self.client.get(reverse('StudentConcern'))
        feed = self.client.get(reverse('activity_feed'), {'after': last}).json()
        self.assertEqual(len(feed['rows']), 1)

    def test_admin_edit_delete_concern(self):
        self.as_admin()
        response = self.client.post(reverse('concern_update', args=[self.mine.pk]), {
            'Fullname': 'Juan Cruz', 'StudentID': 1001, 'College': CCS, 'category': 'Academic',
            'priority': 'Low', 'status': 'In Review', 'Concern': 'Edited'})
        self.assertEqual(response.status_code, 302)
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.status, 'In Review')
        self.client.post(reverse('concern_delete', args=[self.mine.pk]))
        self.assertFalse(StudentConcern.objects.filter(pk=self.mine.pk).exists())

    def test_my_concerns_scope(self):
        self.as_student()
        html = self.client.get(reverse('StudentConcern'), {'mine': '1'}).content.decode()
        self.assertIn('Broken aircon', html)
        self.assertNotIn('Library hours', html)

    def test_csv_export_respects_anonymity(self):
        self.as_staff()
        body = self.client.get(reverse('export_csv')).content.decode()
        self.assertIn('Anonymous Participant', body)
        self.assertNotIn('Maria Lopez', body)
        self.client.post(reverse('logout'))
        self.as_admin()
        body = self.client.get(reverse('export_csv')).content.decode()
        self.assertIn('Maria Lopez', body)

    def test_login_page_and_pages_render(self):
        html = self.client.get(reverse('login')).content.decode()
        self.assertIn('Login as Student', html)
        self.assertIn('Login as Staff', html)
        self.as_admin()
        for name in ('StudentConcern', 'concern_create', 'accounts_list', 'activity_logs', 'account_create', 'chat_room'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


    def test_chat_requires_login(self):
        self.assertEqual(self.client.get(reverse('chat_room')).status_code, 302)
        self.assertEqual(self.client.post(reverse('chat_send'), {'message': 'hi'}).status_code, 302)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_everyone_can_chat_with_role_tags(self):
        for login, role in ((self.as_student, 'student'), (self.as_staff, 'staff'), (self.as_admin, 'admin')):
            login()
            response = self.client.post(reverse('chat_send'), {'message': f'hello from {role}'})
            self.assertEqual(response.status_code, 302)
            self.client.post(reverse('logout'))
        self.assertEqual(
            list(ChatMessage.objects.values_list('author_role', flat=True)), ['student', 'staff', 'admin'])
        self.as_student()
        html = self.client.get(reverse('chat_room')).content.decode()
        for role in ('student', 'staff', 'admin'):
            self.assertIn(f'hello from {role}', html)
            self.assertIn(f'tag role-{role}', html)
        log = html.split('<ul class="chat-log"')[1].split('</ul>')[0]
        self.assertEqual(log.count('data-act="delete"'), 1)

    def test_chat_feed_and_ajax_send(self):
        self.as_student()
        response = self.client.post(
            reverse('chat_send'), {'message': 'live one'}, headers={'X-Requested-With': 'XMLHttpRequest'})
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['message']['own'])
        self.assertEqual(data['message']['role'], 'student')
        self.client.post(reverse('logout'))
        self.as_staff()
        feed = self.client.get(reverse('chat_feed'), {'after': 0}).json()
        self.assertEqual(feed['messages'][0]['text'], 'live one')
        self.assertFalse(feed['messages'][0]['own'])
        self.assertEqual(self.client.get(reverse('chat_feed'), {'after': feed['last_id']}).json()['messages'], [])

    def test_chat_rejects_empty_and_floods(self):
        self.as_student()
        self.client.post(reverse('chat_send'), {'message': '   '})
        self.assertEqual(ChatMessage.objects.count(), 0)
        for n in range(8):
            self.client.post(reverse('chat_send'), {'message': f'spam {n}'})
        self.assertEqual(ChatMessage.objects.count(), 5)

    def test_chat_is_logged_and_deletion_rules(self):
        self.as_student()
        self.client.post(reverse('chat_send'), {'message': 'moderate me'})
        message = ChatMessage.objects.get()
        self.assertTrue(ActivityLog.objects.filter(action='chat_message', StudentID='1001').exists())
        self.client.post(reverse('logout'))
        self.as_staff()
        self.assertEqual(self.client.post(reverse('chat_delete', args=[message.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('chat_edit', args=[message.pk]), {'message': 'hax'}).status_code, 403)
        self.client.post(reverse('logout'))
        self.as_admin()
        self.assertIn('data-act="delete"', self.client.get(reverse('chat_room')).content.decode())
        self.client.post(reverse('chat_delete', args=[message.pk]))
        message.refresh_from_db()
        self.assertIsNotNone(message.deleted_at)
        self.assertEqual(message.message, '')
        self.assertNotIn('moderate me', self.client.get(reverse('chat_room')).content.decode())
        self.assertTrue(ActivityLog.objects.filter(action='chat_delete').exists())

    def test_own_message_edit_and_delete_within_30_seconds(self):
        self.as_student()
        self.client.post(reverse('chat_send'), {'message': 'typo mesage'})
        message = ChatMessage.objects.get()
        response = self.client.post(reverse('chat_edit', args=[message.pk]), {'message': 'fixed message'})
        self.assertTrue(response.json()['message']['edited'])
        message.refresh_from_db()
        self.assertEqual(message.message, 'fixed message')
        self.assertTrue(ActivityLog.objects.filter(action='chat_edit').exists())
        self.assertEqual(self.client.post(reverse('chat_delete', args=[message.pk])).status_code, 302)
        message.refresh_from_db()
        self.assertIsNotNone(message.deleted_at)

    def test_edit_and_delete_locked_after_30_seconds(self):
        self.as_staff()
        self.client.post(reverse('chat_send'), {'message': 'permanent now'})
        message = ChatMessage.objects.get()
        ChatMessage.objects.filter(pk=message.pk).update(created_at=timezone.now() - timedelta(seconds=31))
        self.assertEqual(self.client.post(reverse('chat_edit', args=[message.pk]), {'message': 'late'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('chat_delete', args=[message.pk]), {}).status_code, 403)
        message.refresh_from_db()
        self.assertEqual(message.message, 'permanent now')
        self.assertIsNone(message.deleted_at)
        html = self.client.get(reverse('chat_room')).content.decode()
        self.assertNotIn('data-act="edit"', html)

    def test_feed_propagates_edits_and_deletes(self):
        self.as_student()
        self.client.post(reverse('chat_send'), {'message': 'first'})
        message = ChatMessage.objects.get()
        self.client.post(reverse('logout'))
        self.as_staff()
        since = timezone.now().timestamp() - 1
        ChatMessage.objects.filter(pk=message.pk).update(updated_at=timezone.now())
        feed = self.client.get(reverse('chat_feed'), {'after': message.pk, 'since': since}).json()
        self.assertEqual(feed['messages'], [])
        self.assertEqual(feed['changed'][0]['id'], message.pk)
        message.mark_deleted()
        feed = self.client.get(reverse('chat_feed'), {'after': message.pk, 'since': since}).json()
        self.assertEqual(feed['changed'], [{'id': message.pk, 'deleted': True}])

    def test_chat_layout_marks_own_messages(self):
        self.as_student()
        self.client.post(reverse('chat_send'), {'message': 'mine'})
        ChatMessage.objects.create(account=self.staff, author_name='Ana Reyes', author_role='staff', message='theirs')
        html = self.client.get(reverse('chat_room')).content.decode()
        self.assertEqual(html.count('chat-msg own'), 1)
        self.assertIn('Ana Reyes', html)

    def test_side_panel_for_students_and_staff_only(self):
        for login in (self.as_student, self.as_staff):
            login()
            html = self.client.get(reverse('StudentConcern')).content.decode()
            self.assertIn('class="sidenav"', html)
            for label in ('>Concerns<', '>Public Chat<', 'Private Chat'):
                self.assertIn(label, html)
            self.assertNotIn('My Concerns</a>', html)
            self.assertNotIn('Total concerns', html)
            self.assertNotIn('class="nav"', html)
            self.client.post(reverse('logout'))
        self.as_admin()
        html = self.client.get(reverse('StudentConcern')).content.decode()
        self.assertNotIn('class="sidenav"', html)
        self.assertIn('class="nav"', html)
        self.assertNotIn('My Concerns</a>', html)
        self.assertIn('Total concerns', html)

    def test_private_chat_search_by_id_or_name(self):
        self.as_student()
        html = self.client.get(reverse('private_chat'), {'q': '1002'}).content.decode()
        self.assertIn('ID 1002', html)
        self.assertNotIn('Maria Lopez', html.split('class="people"')[1])
        html = self.client.get(reverse('private_chat'), {'q': 'ana'}).content.decode()
        self.assertIn('Ana Reyes', html)
        html = self.client.get(reverse('private_chat'), {'q': 'maria'}).content.decode()
        self.assertIn('ID 1002', html)
        html = self.client.get(reverse('private_chat'), {'q': 'AdminSCS'}).content.decode()
        self.assertNotIn('AdminSCS</span>', html)
        self.assertNotIn('ID 1001</span>', self.client.get(reverse('private_chat'), {'q': 'juan'}).content.decode())

    def test_private_messages_are_private(self):
        self.as_student()
        response = self.client.post(
            reverse('private_send', args=[self.other.pk]), {'message': 'secret hello'},
            headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertTrue(response.json()['ok'])
        self.assertTrue(response.json()['message']['own'])
        log = ActivityLog.objects.get(action='private_message')
        self.assertEqual(log.detail, 'To ID 1002')
        self.assertNotIn('secret hello', log.detail)
        self.client.post(reverse('logout'))
        self.as_staff()
        html = self.client.get(reverse('private_thread', args=[self.other.pk])).content.decode()
        self.assertNotIn('secret hello', html)
        feed = self.client.get(reverse('private_feed', args=[self.other.pk]), {'after': 0}).json()
        self.assertEqual(feed['messages'], [])
        self.client.post(reverse('logout'))
        self.login(role='student', Fullname='Maria Lopez', StudentID=1002)
        home = self.client.get(reverse('StudentConcern')).content.decode()
        self.assertIn('class="badge">1<', home)
        html = self.client.get(reverse('private_thread', args=[self.student.pk])).content.decode()
        self.assertIn('secret hello', html)
        self.assertIn('ID 1001', html)
        self.assertNotIn('Juan Cruz', html.split('class="dm"')[1])
        self.assertIsNotNone(PrivateMessage.objects.get().read_at)
        self.assertNotIn('class="badge">1<', self.client.get(reverse('StudentConcern')).content.decode())

    def test_private_chat_live_feed_and_edit_rules(self):
        self.as_student()
        self.client.post(reverse('private_send', args=[self.staff.pk]), {'message': 'hello staff'})
        message = PrivateMessage.objects.get()
        edited = self.client.post(reverse('private_edit', args=[message.pk]), {'message': 'hello again'}).json()
        self.assertTrue(edited['message']['edited'])
        self.client.post(reverse('logout'))
        self.as_staff()
        feed = self.client.get(reverse('private_feed', args=[self.student.pk]), {'after': 0}).json()
        self.assertEqual(feed['messages'][0]['text'], 'hello again')
        self.assertEqual(feed['messages'][0]['name'], 'ID 1001')
        self.assertFalse(feed['messages'][0]['can_edit'])
        self.assertEqual(self.client.post(reverse('private_edit', args=[message.pk]), {'message': 'x'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('private_delete', args=[message.pk])).status_code, 403)
        self.client.post(reverse('logout'))
        self.as_student()
        PrivateMessage.objects.filter(pk=message.pk).update(created_at=timezone.now() - timedelta(seconds=40))
        self.assertEqual(self.client.post(reverse('private_delete', args=[message.pk])).status_code, 403)

    def test_private_chat_blocked_for_admin_and_self(self):
        self.as_admin()
        self.assertEqual(self.client.get(reverse('private_chat')).status_code, 403)
        self.client.post(reverse('logout'))
        self.as_student()
        self.assertEqual(self.client.get(reverse('private_thread', args=[self.student.pk])).status_code, 302)
        self.assertEqual(self.client.get(reverse('private_thread', args=[self.admin.pk])).status_code, 404)
        self.client.post(reverse('private_send', args=[self.student.pk]), {'message': 'me'})
        self.assertEqual(PrivateMessage.objects.count(), 0)

    def test_partner_listed_before_first_message(self):
        self.as_student()
        html = self.client.get(reverse('private_thread', args=[self.other.pk])).content.decode()
        self.assertIn('New conversation', html)
        self.assertNotIn('No conversations yet', html)
