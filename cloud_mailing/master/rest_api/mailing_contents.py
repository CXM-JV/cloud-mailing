import email
import email.errors
import email.message

from twisted.web import server
from twisted.web.resource import Resource

from ...common import http_status
from ...common.rest_api_common import ApiResource
from ...common.db_common import get_db

__author__ = 'Cedric RICARD'


# noinspection PyPep8Naming
class MailingContentApi(ApiResource):
    """
    Display mailing content
    """
    def __init__(self, mailing_id=None):
        Resource.__init__(self)
        self.mailing_id = mailing_id

    def render_GET(self, request):
        self.log_call(request)
        db = get_db()
        db.mailing.find_one({'_id': self.mailing_id})\
            .addCallback(self.cb_get_mailing, request)\
            .addErrback(self.eb_get_mailing, request)
        return server.NOT_DONE_YET

    def cb_get_mailing(self, mailing, request):
        mparser = email.parser.FeedParser()
        mparser.feed(mailing['header'])
        mparser.feed(mailing['body'])
        msg = mparser.close()

        def get_html_body(part):
            self.log.debug("***")
            import email.message
            assert (isinstance(part, email.message.Message))
            if part.is_multipart():
                self.log.debug(part.get_content_type())
                subtype = part.get_content_subtype()
                if subtype == 'mixed':
                    return get_html_body(part.get_payload(0))

                elif subtype == 'alternative':
                    for p in part.get_payload():
                        self.log.debug("  sub = %s", p.get_content_type())
                        if p.get_content_type() == 'text/html' or p.get_content_type() == "multipart/related":
                            return get_html_body(p)

                elif subtype == 'digest':
                    raise email.errors.MessageParseError, "multipart/digest not supported"

                elif subtype == 'parallel':
                    raise email.errors.MessageParseError, "multipart/parallel not supported"

                elif subtype == 'related':
                    return get_html_body(part.get_payload(0))

                else:
                    self.log.warn("Unknown multipart subtype '%s'" % subtype)

            else:
                maintype, subtype = part.get_content_type().split('/')
                if maintype == 'text':
                    self.log.debug("body found (%s/%s)", maintype, subtype)
                    # request.setHeader('Content-Type', part.get_content_type())
                    part_body = part.get_payload().encode('utf8')
                    self.log.debug("body type: %s", type(part_body))
                    return part_body
                else:
                    self.log.warn("get_html_body(): can't handle '%s' parts" % part.get_content_type())
            return ""

        request.setResponseCode(http_status.HTTP_200_OK)
        body = get_html_body(msg)
        self.log.debug("**body: %s", type(body))

        request.write(get_html_body(msg))
        # request.write("<html><body><b>Email</b> content.</body></html>")
        request.finish()

    def eb_get_mailing(self, error, request):
        self.log.error("Error returning HTML content for mailing [%d]: %s", self.mailing_id, error)
        request.setResponseCode(http_status.HTTP_500_INTERNAL_SERVER_ERROR)
        request.write("<html><body><b>ERROR</b>: can't get content.</body></html>")
        request.finish()