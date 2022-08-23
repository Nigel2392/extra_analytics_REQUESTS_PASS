from django.db.models import F
from .models import Analytics,UserAnalytics,UserAnalyticsMeta
# import threading
from django.utils import timezone
from django.conf import settings
import re
import threading
from urllib.parse import urlencode
from datetime import datetime
from django.utils.timezone import make_aware

def _get_session_id(request):
    # Gets or creates a session ID for a given request.
    session_id = request.session.session_key
    created = False
    if not session_id:
        session_id = request.session.create()
        created = True
    return session_id, created

def _get_client_ip(request):
    # Gets the client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def _get_current_page(request):
    # Gets the current page the user is on.
    try:
        if request.GET:
            extra_url = '?'+ urlencode(request.GET)
        else:
            extra_url = ''
        return f"{request.path}{extra_url}"
    except:
        return request.path

def stats(os_info,object):
    # Increment the OS analytics object based on the HTTP_USER_AGENT
    if 'Windows' in os_info:
        object.update(win=F("win")+1)
    elif 'Linux' in os_info:
        object.update(linux=F("linux")+1)
    elif 'Mac' in os_info:
        object.update(mac=F("mac")+1)
    elif 'Android' in os_info:
        object.update(android=F("android")+1)
    elif 'iPhone' in os_info:
        object.update(iphone=F("iph")+1)
    else:
        object.update(other=F("oth")+1)

def Track_User(request):
    # Get some basic metadata about the request
    session_id,created = _get_session_id(request)
    if created:
        request.session.modified = True
    client_ip = _get_client_ip(request)
    current_page = _get_current_page(request)
    nowtime = datetime.now()

    # Check if user is authenticated, and an analytics object already exists
    # Uses session ID's if not authenticated.

    if request.user.is_authenticated:
        session_analytics = UserAnalytics.objects.filter(user=request.user)
    else:
        session_analytics = UserAnalytics.objects.filter(sessionid=session_id)
    if len(session_analytics) < 1:
        if session_id != None:
            if request.user.is_authenticated:
                session_analytics = UserAnalytics.objects.create(user=request.user,sessionid=session_id)
            else:
                session_analytics = UserAnalytics.objects.create(sessionid=session_id)
        else:
            return

        # Check if user is authenticated, get OS analytics object.
        if request.user.is_authenticated:
            session_analytics = UserAnalytics.objects.filter(user=request.user)
        else:
            session_analytics = UserAnalytics.objects.filter(sessionid=session_id)
    
    # Get or create a specific analytics object. 
    # Creates a new object for each user every day.
    user_analytics = UserAnalyticsMeta.objects.filter(
        bound_to=session_analytics.first(),
        ip=client_ip,
        current_page=current_page,
        created_at__gte=make_aware(nowtime) - timezone.timedelta(days=1)
    ).order_by('-created_at').first()

    if not user_analytics:
        user_analytics = UserAnalyticsMeta.objects.create(
            bound_to=session_analytics.first(),
            ip=client_ip,
            current_page=current_page,
        )
    
    user_analytics.page_visits += 1
    user_analytics.save()
    # Gets a general OS analytics object. Only one should always exist.x
    general_analytics = Analytics.objects.all()
    if not general_analytics:
        general_analytics = Analytics.objects.create()
    
    # Run the OS analytics through the increment function.
    stats(request.META['HTTP_USER_AGENT'],session_analytics)
    stats(request.META['HTTP_USER_AGENT'],general_analytics)

class TrackMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        ANALYTICS_BLOCKED_PATHS: 
            List of paths that should not be tracked
            Can be set to None

        ANALYTICS_BLOCKED_ROOT_PATH: 
            Single path that should not be tracked
            Can be set to None

        ANALYTICS_DISALLOW_REQUESTS_TO_FILES: 
            If True, requests to files will not be tracked
            Can be set to None
            Default is True

        ANALYTICS_REQUEST_TYPE_BLOCK_LIST: 
            List of request methods that should not be tracked
            Can be set to None
            Default is ['POST']

        BLOCK_AJAX_REQUESTS: 
            If True, AJAX requests will not be tracked
            Can be set to None
            Default is True

        """
        # Convert settings into a dictionary/
        settings_dict = settings.__dict__['_wrapped'].__dict__
 
        # If settings are not set, we set up some basic items to block. 
        blocked_paths = settings_dict.get(
            'ANALYTICS_BLOCKED_PATHS', 
            ['admin','flavicon.ico','static',]
        ) 
        # You probably want to block the site root path.
        block_root_path = settings_dict.get(
            'ANALYTICS_BLOCKED_ROOT_PATH', 
            None
        )
        # This is true by default, otherwise all requests to static files will be counted.
        disallow_requests_to_files = settings_dict.get(
            'ANALYTICS_DISALLOW_REQUESTS_TO_FILES', 
            True
        )
        # Check which request methods the user wants to block. POST is blocked by default.
        blocked_request_types = settings_dict.get(
            'ANALYTICS_REQUEST_TYPE_BLOCK_LIST',
            ['POST']
        )
        # Check if user wants to block ajax requests in settings. 
        block_ajax_requests = settings_dict.get(
            'BLOCK_AJAX_REQUESTS',
            True
        )
        
        # Check if uses wishes to block any of these request types.
        if blocked_request_types:
            if request.method in blocked_request_types:
                return self.get_response(request)

        # If the request is an AJAX request, we probably don't want to track it.
        # Can be turned off in settings.
        if block_ajax_requests:
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                return self.get_response(request)

        # Check if the request path is equal to the given root path.
        if block_root_path == request.path:
            return self.get_response(request)

        # Check if any item of the blocked paths list is in the request path. 
        if blocked_paths:
            for path in blocked_paths:
                if re.search(path, request.path):
                    return self.get_response(request)
        
        # Check if the request path is a file. It does so by checking if the path ends with a file extension.
        # Example:
        # 'style.css' -> True
        # 'index.html' -> True
        # 'index' -> False

        if disallow_requests_to_files:
            if '.' in request.path.split('/')[-1]:
                return self.get_response(request)

        # If none of the conditions were met, we start a thread to track the user.

        threading.Thread(target=Track_User, args=(request,)).start()

        return self.get_response(request)

