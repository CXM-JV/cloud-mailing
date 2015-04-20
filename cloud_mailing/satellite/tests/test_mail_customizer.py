# Copyright 2015 Cedric RICARD
#
# This file is part of CloudMailing.
#
# CloudMailing is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CloudMailing is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with CloudMailing.  If not, see <http://www.gnu.org/licenses/>.

import factory
from ...common.unittest_mixins import DatabaseMixin
from ..mail_customizer import MailCustomizer
from ..models import MailingRecipient, Mailing
from twisted.trial.unittest import TestCase
import factories
import os
import email.parser
import email.message
import base64

__author__ = 'ricard'



class MailCustomizerTestCase(DatabaseMixin, TestCase):
    def setUp(self):
        self.connect_to_db()

    def tearDown(self):
        self.disconnect_from_db()

    def test_customization_with_custom_fields(self):
        recipient = factories.RecipientFactory()


        customizer = MailCustomizer(recipient, use_jinja2=False)
        self.assertEquals(customizer._do_customization(recipient.mailing.body, recipient.contact_data),
                          'This is a very simple mailing.')

    def test_customize_message(self):
        mailing = factories.MailingFactory()
        recipient = factories.RecipientFactory(mailing=mailing)

        customizer = MailCustomizer(recipient, use_jinja2=False)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        # print file(fullpath, 'rt').read()
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        self.assertFalse(message.is_multipart())
        self.assertTrue('Date' in message)
        self.assertEquals(message.get_payload(), 'This is a very simple mailing.')


    def test_customize_message_v2(self):
        mailing = factories.MailingFactory(body = 'This is a {{ custom }} mailing.')
        recipient = factories.RecipientFactory(mailing=mailing)

        customizer = MailCustomizer(recipient, use_jinja2=True)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        self.assertFalse(message.is_multipart())
        self.assertTrue('Date' in message)
        self.assertEquals('This is a very simple mailing.', message.get_payload())


    def test_customize_simple_message_with_recipient_attachment(self):
        recipient = factories.RecipientFactory(
            contact_data={
                'email': 'firstname.lastname@domain.com',
                'custom': 'very simple',
                'attachments': [
                    {
                        'filename': "export.csv",
                        'data': base64.b64encode("col1;col2;col3\nval1;val2;val3\n"),
                        'content-type': 'text/plain',
                        'charset': 'us-ascii',
                    },
                ]
            }
        )
        #factories.MailingContentFactory(mailing=recipient.mailing)
        #print recipient.mailing.content

        customizer = MailCustomizer(recipient, use_jinja2=False)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        self.assertTrue(message.is_multipart())
        # print
        # print message.as_string()
        self.assertEquals(message.get_payload(i=0).get_payload(), 'This is a very simple mailing.')
        self.assertEquals(message.get_payload(i=1).get_payload(), 'col1;col2;col3\nval1;val2;val3\n')


    def test_customize_mixed_message_with_recipient_attachment(self):
        recipient = factories.RecipientFactory(
            mailing = factories.MailingFactory(
                header="""Content-Transfer-Encoding: 7bit
Content-Type: multipart/mixed; boundary="===============2840728917476054151=="
Subject: Great news!
From: Mailing Sender <sender@my-company.biz>
To: <firstname.lastname@domain.com>
Date: Wed, 05 Jun 2013 06:05:56 -0000
""",
                body="""
--===============2840728917476054151==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

This is a very simple mailing.
--===============2840728917476054151==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="common.txt"

This is an attachment common for all recipients.
Nothing else to say...

--===============2840728917476054151==--
"""
            ),
            contact_data={
                'email': 'firstname.lastname@domain.com',
                'custom': 'very simple',
                'attachments': [
                    {
                        'filename': "export.csv",
                        'data': base64.b64encode("col1;col2;col3\nval1;val2;val3\n"),
                        'content-type': 'text/plain',
                        'charset': 'us-ascii',
                    },
                ]
            }
        )

        customizer = MailCustomizer(recipient, use_jinja2=False)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        self.assertTrue(message.is_multipart())
        # print
        # print message.as_string()
        self.assertEquals(message.get_payload(i=0).get_payload(), 'This is a very simple mailing.')
        self.assertIn("This is an attachment common for all recipients.", message.get_payload(i=1).get_payload())
        self.assertEquals(message.get_payload(i=2).get_payload(), 'col1;col2;col3\nval1;val2;val3\n')


    def test_customize_alternative_message_with_recipient_attachment(self):
        recipient = factories.RecipientFactory(
            mailing = factories.MailingFactory(
                header="""Content-Transfer-Encoding: 7bit
Content-Type: multipart/alternative; boundary="===============2840728917476054151=="
Subject: Great news!
From: Mailing Sender <sender@my-company.biz>
To: <firstname.lastname@domain.com>
Date: Wed, 05 Jun 2013 06:05:56 -0000
""",
                body="""
This is a multi-part message in MIME format.
--===============2840728917476054151==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

This is a very simple mailing.
--===============2840728917476054151==
Content-Type: text/html; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

<html><head></head>
<body>
This is <strong> a very simple</strong> <u>mailing</u>.
Nothing else to say...

--===============2840728917476054151==--
"""
            ),
            contact_data={
                'email': 'firstname.lastname@domain.com',
                'custom': 'very simple',
                'attachments': [
                    {
                        'filename': "export.csv",
                        'data': base64.b64encode("col1;col2;col3\nval1;val2;val3\n"),
                        'content-type': 'text/plain',
                        'charset': 'us-ascii',
                    },
                ]
            }
        )

        customizer = MailCustomizer(recipient, use_jinja2=False)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        # print
        # print message.as_string()
        self.assertTrue(message.is_multipart())
        self.assertEquals("multipart/mixed", message.get_content_type())
        self.assertEquals("multipart/alternative", message.get_payload(i=0).get_content_type())
        self.assertEquals(message.get_payload(i=0).get_payload(i=0).get_payload(), 'This is a very simple mailing.')
        self.assertIn("This is <strong> a very simple</strong> <u>mailing</u>.", message.get_payload(i=0).get_payload(i=1).get_payload())
        self.assertEquals(message.get_payload(i=1).get_payload(), 'col1;col2;col3\nval1;val2;val3\n')


    def test_customize_related_message_with_recipient_attachment(self):
        recipient = factories.RecipientFactory(
            mailing = factories.MailingFactory(
                header="""Content-Transfer-Encoding: 7bit
Content-Type: multipart/related; boundary="===============2840728917476054151=="
Subject: Great news!
From: Mailing Sender <sender@my-company.biz>
To: <firstname.lastname@domain.com>
Date: Wed, 05 Jun 2013 06:05:56 -0000
""",
                body="""
This is a multi-part message in MIME format.
--===============2840728917476054151==
Content-Type: text/html; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

<html><head></head>
<body>
This is <strong> a very simple</strong> <u>mailing</u>.
Nothing else to say...
<img id="Image 2"src="cid:part9.06060104.07080402@akema.fr"
                 height="45" width="130" border="0">
</body></html>
--===============2840728917476054151==
Content-Type: image/jpeg;
 name="akema_logo_signatures.jpg"
Content-Transfer-Encoding: base64
Content-ID: <part9.06060104.07080402@akema.fr>
Content-Disposition: inline;
 filename="akema_logo_signatures.jpg"

/9j/4AAQSkZJRgABAQEASABIAAD/4QESRXhpZgAATU0AKgAAAAgABgEaAAUAAAABAAAAVgEb
AAUAAAABAAAAXgEoAAMAAAABAAIAAAExAAIAAAASAAAAZgEyAAIAAAAUAAAAeIdpAAQAAAAB
AAAAjAAAANAAAABIAAAAAQAAAEgAAAABUGFpbnQuTkVUIHYzLjUuMTAAMjAxMjoxMjoxMSAx

--===============2840728917476054151==--
"""
            ),
            contact_data={
                'email': 'firstname.lastname@domain.com',
                'custom': 'very simple',
                'attachments': [
                    {
                        'filename': "export.csv",
                        'data': base64.b64encode("col1;col2;col3\nval1;val2;val3\n"),
                        'content-type': 'text/plain',
                        'charset': 'us-ascii',
                    },
                ]
            }
        )

        customizer = MailCustomizer(recipient, use_jinja2=False)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        # print
        # print message.as_string()
        self.assertTrue(message.is_multipart())
        self.assertEquals("multipart/mixed", message.get_content_type())
        self.assertEquals("multipart/related", message.get_payload(i=0).get_content_type())
        self.assertEquals("image/jpeg", message.get_payload(i=0).get_payload(i=1).get_content_type())
        self.assertIn("This is <strong> a very simple</strong> <u>mailing</u>.", message.get_payload(i=0).get_payload(i=0).get_payload())
        self.assertEquals(message.get_payload(i=1).get_payload(), 'col1;col2;col3\nval1;val2;val3\n')


    def test_customize_alternative_and_related_message_with_recipient_attachment(self):
        recipient = factories.RecipientFactory(
            mailing = factories.MailingFactory(
                header="""Content-Transfer-Encoding: 7bit
Content-Type: multipart/alternative; boundary="===============1111111111111111111=="
Subject: Great news!
From: Mailing Sender <sender@my-company.biz>
To: <firstname.lastname@domain.com>
Date: Wed, 05 Jun 2013 06:05:56 -0000
""",
                body="""
This is a multi-part message in MIME format.
--===============1111111111111111111==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

This is a very simple mailing.
--===============1111111111111111111==
Content-Type: multipart/related; boundary="===============2222222222222222222=="

This is a multi-part message in MIME format.
--===============2222222222222222222==
Content-Type: text/html; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

<html><head></head>
<body>
This is <strong> a very simple</strong> <u>mailing</u>.
Nothing else to say...
<img id="Image 2"src="cid:part9.06060104.07080402@akema.fr"
                 height="45" width="130" border="0">
</body></html>
--===============2222222222222222222==
Content-Type: image/jpeg;
 name="akema_logo_signatures.jpg"
Content-Transfer-Encoding: base64
Content-ID: <part9.06060104.07080402@akema.fr>
Content-Disposition: inline;
 filename="akema_logo_signatures.jpg"

/9j/4AAQSkZJRgABAQEASABIAAD/4QESRXhpZgAATU0AKgAAAAgABgEaAAUAAAABAAAAVgEb
AAUAAAABAAAAXgEoAAMAAAABAAIAAAExAAIAAAASAAAAZgEyAAIAAAAUAAAAeIdpAAQAAAAB
AAAAjAAAANAAAABIAAAAAQAAAEgAAAABUGFpbnQuTkVUIHYzLjUuMTAAMjAxMjoxMjoxMSAx

--===============2222222222222222222==--

--===============1111111111111111111==--
"""
            ),
            contact_data={
                'email': 'firstname.lastname@domain.com',
                'custom': 'very simple',
                'attachments': [
                    {
                        'filename': "export.csv",
                        'data': base64.b64encode("col1;col2;col3\nval1;val2;val3\n"),
                        'content-type': 'text/plain',
                        'charset': 'us-ascii',
                    },
                ]
            }
        )

        customizer = MailCustomizer(recipient, use_jinja2=False)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        # print
        # print message.as_string()
        self.assertTrue(message.is_multipart())
        self.assertEquals("multipart/mixed",       message.get_content_type())
        self.assertEquals("multipart/alternative", message.get_payload(i=0).get_content_type())
        self.assertEquals("text/plain",            message.get_payload(i=0).get_payload(i=0).get_content_type())
        self.assertEquals("multipart/related",     message.get_payload(i=0).get_payload(i=1).get_content_type())
        self.assertEquals('This is a very simple mailing.', message.get_payload(i=0).get_payload(i=0).get_payload())
        self.assertIn("This is <strong> a very simple</strong> <u>mailing</u>.", message.get_payload(i=0).get_payload(i=1).get_payload(i=0).get_payload())
        self.assertEquals(message.get_payload(i=1).get_payload(), 'col1;col2;col3\nval1;val2;val3\n')


    def test_customize_mixed_and_alternative_and_related_message_with_recipient_attachment(self):
        recipient = factories.RecipientFactory(
            mailing = factories.MailingFactory(
                header="""Content-Transfer-Encoding: 7bit
Content-Type: multipart/mixed; boundary="===============0000000000000000000=="
Subject: Great news!
From: Mailing Sender <sender@my-company.biz>
To: <firstname.lastname@domain.com>
Date: Wed, 05 Jun 2013 06:05:56 -0000
""",
                body="""
This is a multi-part message in MIME format.
--===============0000000000000000000==
Content-Type: multipart/alternative; boundary="===============1111111111111111111=="

--===============1111111111111111111==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

This is a very simple mailing.
--===============1111111111111111111==
Content-Type: multipart/related; boundary="===============2222222222222222222=="

This is a multi-part message in MIME format.
--===============2222222222222222222==
Content-Type: text/html; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

<html><head></head>
<body>
This is <strong> a very simple</strong> <u>mailing</u>.
Nothing else to say...
<img id="Image 2"src="cid:part9.06060104.07080402@akema.fr"
                 height="45" width="130" border="0">
</body></html>
--===============2222222222222222222==
Content-Type: image/jpeg;
 name="akema_logo_signatures.jpg"
Content-Transfer-Encoding: base64
Content-ID: <part9.06060104.07080402@akema.fr>
Content-Disposition: inline;
 filename="akema_logo_signatures.jpg"

/9j/4AAQSkZJRgABAQEASABIAAD/4QESRXhpZgAATU0AKgAAAAgABgEaAAUAAAABAAAAVgEb
AAUAAAABAAAAXgEoAAMAAAABAAIAAAExAAIAAAASAAAAZgEyAAIAAAAUAAAAeIdpAAQAAAAB
AAAAjAAAANAAAABIAAAAAQAAAEgAAAABUGFpbnQuTkVUIHYzLjUuMTAAMjAxMjoxMjoxMSAx

--===============2222222222222222222==--

--===============1111111111111111111==--

--===============0000000000000000000==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="common.txt"

This is an attachment common for all recipients.
Nothing else to say...

--===============0000000000000000000==--

"""
            ),
            contact_data={
                'email': 'firstname.lastname@domain.com',
                'custom': 'very simple',
                'attachments': [
                    {
                        'filename': "export.csv",
                        'data': base64.b64encode("col1;col2;col3\nval1;val2;val3\n"),
                        'content-type': 'text/plain',
                        'charset': 'us-ascii',
                    },
                ]
            }
        )

        customizer = MailCustomizer(recipient, use_jinja2=False)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        # print
        # print message.as_string()
        self.assertTrue(message.is_multipart())
        self.assertEquals("multipart/mixed",       message.get_content_type())
        self.assertEquals("multipart/alternative", message.get_payload(i=0).get_content_type())
        self.assertEquals("text/plain",            message.get_payload(i=0).get_payload(i=0).get_content_type())
        self.assertEquals("multipart/related",     message.get_payload(i=0).get_payload(i=1).get_content_type())
        self.assertEquals('This is a very simple mailing.', message.get_payload(i=0).get_payload(i=0).get_payload())
        self.assertIn("This is <strong> a very simple</strong> <u>mailing</u>.", message.get_payload(i=0).get_payload(i=1).get_payload(i=0).get_payload())
        self.assertIn("This is an attachment", message.get_payload(i=1).get_payload())
        self.assertEquals(message.get_payload(i=2).get_payload(), 'col1;col2;col3\nval1;val2;val3\n')


    def test_clicks_tracking(self):
        mailing = factories.MailingFactory(tracking_url='http://tracking.net/')
        recipient = factories.RecipientFactory(mailing=mailing, tracking_id="TRACKING_ID")

        customizer = MailCustomizer(recipient, use_jinja2=True, read_tracking=False, click_tracking=True)
        content = '<p>Please <a href="http://www.mydomain.com/the_page?p=parameter">click here</a></p>'
        new_content = customizer._do_customization_jinja2(
            body=content,
            contact_data=customizer.make_contact_data_dict(recipient),
            is_html=True
        )
        self.assertEquals(
            # '<p>Please <a href="http://tracking.net/c/?o=http://www.mydomain.com/the_page?p=parameter">click here</a></p>',
            '<p>Please <a href="http://tracking.net/c/TRACKING_ID/?o=http%3A//www.mydomain.com/the_page%3Fp%3Dparameter'
                    '&t=http%3A//www.mydomain.com/the_page%3Fp%3Dparameter">click here</a></p>',
            new_content)


    def test_clicks_tracking_with_customized_links(self):
        mailing = factories.MailingFactory(tracking_url='http://tr.net/')
        recipient = factories.RecipientFactory(mailing=mailing,
                                               tracking_id="TRACKING_ID",
                                               contact_data={
                                                   'email': 'contact@company.com',
                                                   'id': 123
                                               })

        customizer = MailCustomizer(recipient, use_jinja2=True, read_tracking=False, click_tracking=True)
        content = '<p>Please <a href="http://my.com/the_page?id={{ id }}">click here</a></p>'
        new_content = customizer._do_customization_jinja2(
            body=content,
            contact_data=customizer.make_contact_data_dict(recipient),
            is_html=True
        )
        self.assertEquals(
            '<p>Please <a href="http://tr.net/c/TRACKING_ID/?o=http%3A//my.com/the_page%3Fid%3D%7B%7B%20id%20%7D%7D'
                    '&t=http%3A//my.com/the_page%3Fid%3D123">click here</a></p>',
            new_content)

    def test_customize_message_encoding(self):
        mailing = factories.MailingFactory(
            header="""Content-Transfer-Encoding: 7bit
Content-Type: multipart/alternative; boundary="===============2840728917476054151=="
Subject: Great news!
From: Mailing Sender <sender@my-company.biz>
To: <firstname.lastname@domain.com>
Date: Wed, 05 Jun 2013 06:05:56 -0000
""",
            body="""
This is a multi-part message in MIME format.
--===============2840728917476054151==
Content-Type: text/plain; charset="iso-8859-1"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable

This is a very simple mailing. I'm happy.
--===============2840728917476054151==
Content-Type: text/html; charset="iso-8859-1"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html><head>
<META http-equiv=3DContent-Type content=3D"text/html; charset=3Diso-8859-1">
</head>
<body>
This is <strong> a very simple</strong> <u>mailing</u>. =
I'm happy! Nothing else to say...
</body></html>

--===============2840728917476054151==--
"""
        )
        recipient = factories.RecipientFactory(mailing=mailing)

        customizer = MailCustomizer(recipient, use_jinja2=False)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        self.assertTrue(message.is_multipart())
        self.assertEquals("multipart/alternative", message.get_content_type())
        self.assertEquals("text/plain", message.get_payload(i=0).get_content_type())
        self.assertEquals("text/html", message.get_payload(i=1).get_content_type())
        self.assertEquals(message.get_payload(i=0).get_payload(decode=True), "This is a very simple mailing. I'm happy.")
        self.assertIn("This is <strong> a very simple</strong> <u>mailing</u>. I'm happy! ", message.get_payload(i=1).get_payload(decode=True))


    def test_customize_message_bad_encoding_iso_8859_1_from_msword(self):
        """
        Test a boggus situation when MS Word encode HTML with Windows-1252 charset,
        but declaring it as ISO-8859-1.
        Example: character 0x92 isn't defined in ISO-8859-1, but exists in
        Windows-1252 and represents a lovely apostrophe
        """
        mailing = factories.MailingFactory(
            header="""Content-Transfer-Encoding: 7bit
Content-Type: multipart/alternative; boundary="===============2840728917476054151=="
Subject: Great news!
From: Mailing Sender <sender@my-company.biz>
To: <firstname.lastname@domain.com>
Date: Wed, 05 Jun 2013 06:05:56 -0000
""",
            body="""
This is a multi-part message in MIME format.
--===============2840728917476054151==
Content-Type: text/plain; charset="iso-8859-1"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable

This is a very simple mailing. I=92m happy.
--===============2840728917476054151==
Content-Type: text/html; charset="iso-8859-1"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html><head>
<META http-equiv=3DContent-Type content=3D"text/html; charset=3Diso-8859-1">
</head>
<body>
This is <strong> a very simple</strong> <u>mailing</u>. =
I=92m happy! Nothing else to say...
</body></html>

--===============2840728917476054151==--
"""
        )
        recipient = factories.RecipientFactory(mailing=mailing)

        return
        customizer = MailCustomizer(recipient, use_jinja2=False)
        fullpath = os.path.join(customizer.temp_path, customizer.make_file_name())
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.assertFalse(os.path.exists(fullpath))

        customizer._run_customizer()

        self.assertTrue(os.path.exists(fullpath))
        parser = email.parser.Parser()
        message = parser.parse(file(fullpath, 'rt'), headersonly = False)
        assert(isinstance(message, email.message.Message))
        self.assertTrue(message.is_multipart())
        self.assertEquals("multipart/alternative", message.get_content_type())
        self.assertEquals("text/plain", message.get_payload(i=0).get_content_type())
        self.assertEquals("text/html", message.get_payload(i=1).get_content_type())
        self.assertEquals("This is a very simple mailing. I\x92m happy.", message.get_payload(i=0).get_payload(decode=True))
        self.assertIn("This is <strong> a very simple</strong> <u>mailing</u>. I\x92m happy! ", message.get_payload(i=1).get_payload(decode=True))
