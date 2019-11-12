from .rest_api_base import *

class SubscriptionMethods():
    def __init__(self, rest_api_base: TableauRestApiBase):
        self.rest_api_base = rest_api_base

    def __getattr__(self, attr):
        return getattr(self.rest_api_base, attr)

    def query_subscriptions(self, username_or_luid: Optional[str] = None, schedule_name_or_luid: Optional[str] = None,
                            subscription_subject: Optional[str] = None, view_or_workbook: Optional[str] = None,
                            content_name_or_luid: Optional[str] = None,
                            project_name_or_luid: Optional[str] = None,
                            wb_name_or_luid: Optional[str] = None) -> etree.Element:

        self.start_log_block()
        subscriptions = self.query_resource('subscriptions')
        filters_dict = {}
        if subscription_subject is not None:
            filters_dict['subject'] = '[@subject="{}"]'.format(subscription_subject)
        if schedule_name_or_luid is not None:
            if self.is_luid(schedule_name_or_luid):
                filters_dict['sched'] = 'schedule[@id="{}"'.format(schedule_name_or_luid)
            else:
                filters_dict['sched'] = 'schedule[@user="{}"'.format(schedule_name_or_luid)
        if username_or_luid is not None:
            if self.is_luid(username_or_luid):
                filters_dict['user'] = 'user[@id="{}"]'.format(username_or_luid)
            else:
                filters_dict['user'] = 'user[@name="{}"]'.format(username_or_luid)
        if view_or_workbook is not None:
            if view_or_workbook not in ['View', 'Workbook']:
                raise InvalidOptionException("view_or_workbook must be 'Workbook' or 'View'")
            # Does this search make sense my itself?

        if content_name_or_luid is not None:
            if self.is_luid(content_name_or_luid):
                filters_dict['content_luid'] = 'content[@id="{}"'.format(content_name_or_luid)
            else:
                if view_or_workbook is None:
                    raise InvalidOptionException('view_or_workbook must be specified for content: "Workook" or "View"')
                if view_or_workbook == 'View':
                    if wb_name_or_luid is None:
                        raise InvalidOptionException('Must include wb_name_or_luid for a View name lookup')
                    content_luid = self.query_workbook_view_luid(wb_name_or_luid, content_name_or_luid,
                                                                 proj_name_or_luid=project_name_or_luid)
                elif view_or_workbook == 'Workbook':
                    content_luid = self.query_workbook_luid(content_name_or_luid, project_name_or_luid)
                filters_dict['content_luid'] = 'content[@id="{}"'.format(content_luid)

        if 'subject' in filters_dict:
            subscriptions = subscriptions.findall('.//t:subscription{}'.format(filters_dict['subject']))
        if 'user' in filters_dict:
            subscriptions = subscriptions.findall('.//t:subscription/{}/..'.format(filters_dict['user']))
        if 'sched' in filters_dict:
            subscriptions = subscriptions.findall('.//t:subscription/{}/..'.format(filters_dict['sched']))
        if 'content_luid' in filters_dict:
            subscriptions = subscriptions.findall('.//t:subscription/{}/..'.format(filters_dict['content_luid']))
        self.end_log_block()
        return subscriptions

    def create_subscription(self, subscription_subject: Optional[str] = None, view_or_workbook: Optional[str] = None,
                            content_name_or_luid: Optional[str] = None, schedule_name_or_luid: Optional[str] = None,
                            username_or_luid: Optional[str] = None, project_name_or_luid: Optional[str] = None,
                            wb_name_or_luid: Optional[str] = None,
                            direct_xml_request: Optional[etree.Element] = None) -> str:
        self.start_log_block()
        if direct_xml_request is not None:
            tsr = direct_xml_request
        else:
            if view_or_workbook not in ['View', 'Workbook']:
                raise InvalidOptionException("view_or_workbook must be 'Workbook' or 'View'")

            user_luid = self.query_user_luid(username_or_luid)
            schedule_luid = self.query_schedule_luid(schedule_name_or_luid)

            if self.is_luid(content_name_or_luid):
                content_luid = content_name_or_luid
            else:
                if view_or_workbook == 'View':
                    if wb_name_or_luid is None:
                        raise InvalidOptionException('Must include wb_name_or_luid for a View name lookup')
                    content_luid = self.query_workbook_view_luid(wb_name_or_luid, content_name_or_luid,
                                                                 proj_name_or_luid=project_name_or_luid, username_or_luid=user_luid)
                elif view_or_workbook == 'Workbook':
                    content_luid = self.query_workbook_luid(content_name_or_luid, project_name_or_luid, user_luid)
                else:
                    raise InvalidOptionException("view_or_workbook must be 'Workbook' or 'View'")

            tsr = etree.Element('tsRequest')
            s = etree.Element('subscription')
            s.set('subject', subscription_subject)
            c = etree.Element('content')
            c.set('type', view_or_workbook)
            c.set('id', content_luid)
            sch = etree.Element('schedule')
            sch.set('id', schedule_luid)
            u = etree.Element('user')
            u.set('id', user_luid)
            s.append(c)
            s.append(sch)
            s.append(u)
            tsr.append(s)

        url = self.build_api_url('subscriptions')
        try:
            new_subscription = self.send_add_request(url, tsr)
            new_subscription_luid = new_subscription.findall('.//t:subscription', self.ns_map)[0].get("id")
            self.end_log_block()
            return new_subscription_luid
        except RecoverableHTTPException as e:
            self.end_log_block()
            raise e

    def create_subscription_to_workbook(self, subscription_subject, wb_name_or_luid, schedule_name_or_luid,
                                        username_or_luid, project_name_or_luid=None):
        """
        :type subscription_subject: unicode
        :type wb_name_or_luid: unicode
        :type schedule_name_or_luid: unicode
        :type username_or_luid: unicode
        :type project_name_or_luid: unicode
        :rtype: unicode
        """
        self.start_log_block()
        luid = self.create_subscription(subscription_subject, 'Workbook', wb_name_or_luid, schedule_name_or_luid,
                                        username_or_luid, project_name_or_luid=project_name_or_luid)
        self.end_log_block()
        return luid

    def create_subscription_to_view(self, subscription_subject, view_name_or_luid, schedule_name_or_luid,
                                    username_or_luid, wb_name_or_luid=None, project_name_or_luid=None):
        """
        :type subscription_subject: unicode
        :type view_name_or_luid: unicode
        :type schedule_name_or_luid:
        :type username_or_luid: unicode
        :type wb_name_or_luid: unicode
        :type project_name_or_luid: unicode
        :rtype: unicode
        """
        self.start_log_block()
        luid = self.create_subscription(subscription_subject, 'View', view_name_or_luid, schedule_name_or_luid,
                                        username_or_luid, wb_name_or_luid=wb_name_or_luid, project_name_or_luid=project_name_or_luid)
        self.end_log_block()
        return luid

    def update_subscription(self, subscription_luid: str, subject: Optional[str] = None,
                            schedule_luid: Optional[str] = None) -> etree.Element:
        if subject is None and schedule_luid is None:
            raise InvalidOptionException("You must pass one of subject or schedule_luid, or both")
        tsr = etree.Element('tsRequest')
        s = etree.Element('subscription')

        if subject is not None:
            s.set('subject', subject)

        if schedule_luid is not None:
            sch = etree.Element('schedule')
            sch.set('id', schedule_luid)
            s.append(sch)
        tsr.append(s)

        url = self.build_api_url("subscriptions/{}".format(subscription_luid))
        response = self.send_update_request(url, tsr)
        self.end_log_block()
        return response

    def delete_subscriptions(self, subscription_luid_s: Union[List[str], str]):
        self.start_log_block()
        subscription_luids = self.to_list(subscription_luid_s)
        for subscription_luid in subscription_luids:
            url = self.build_api_url("subscriptions/{}".format(subscription_luid))
            self.send_delete_request(url)
        self.end_log_block()