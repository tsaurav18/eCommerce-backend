
import os
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from communityapi import views_files
from ecombackend import settings

router = SimpleRouter()
router.register('get_csrf', views_files.GetCsrfView, basename='get_csrf')
router.register('get_stories', views_files.GetActiveStoriesView, basename='get_stories')
router.register('mark_story_viewed', views_files.MarkStoryViewedView, basename='mark_story_viewed')
router.register('mark_story_liked', views_files.MarkStoryLikedView, basename='mark_story_liked')
router.register('upload_story', views_files.CreateStoryView, basename='upload_story')
router.register('get_live_stream', views_files.GetLiveStreamListView, basename='get_live_stream')
router.register('start_live_streaming', views_files.CreateLiveStreamView, basename='start_live_streaming')
router.register('create_live_room_id', views_files.CreateStreamIdView, basename='create_live_stream_id')

urlpatterns = [
    # auth api
    path('', include(router.urls))
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)