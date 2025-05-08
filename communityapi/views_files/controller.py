import traceback
import requests
from rest_framework import mixins, viewsets, status
from django.middleware.csrf import get_token
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from api.utility_files.utils import save_video, save_image
from communityapi.models import LiveStream, LiveStreamComment, Story, UserFollow
from communityapi.serializers_files.serializers import (
    LiveStreamSerializer,
    LiveStreamCommentSerializer,
    StorySerializer,
    UserFollowSerializer,
)
from api.utility_files.api_call import get_body_data, api_success, api_failed
from django.contrib.auth import get_user_model
from django.db.models import Case, When, BooleanField, Value

from ecombackend import settings


class GetCsrfView(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = []

    def list(self, request, *args, **kwargs):
        token = get_token(request)
        return Response({'token': token}, status=status.HTTP_200_OK)
User = get_user_model()

# -------------------------------
# LiveStream Views
# -------------------------------

class CreateLiveStreamView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Create a new live stream.
    """
    queryset = LiveStream.objects.all()
    serializer_class = LiveStreamSerializer
    def createStreamid(self):
        try:
            url = "https://api.videosdk.live/v2/rooms"
            headers = {
                "authorization": settings.STREAM_TOKEN,
                "Content-Type": "application/json",
            }
            response = requests.post(url, headers=headers, json={})
            response.raise_for_status()  # Raises an error for bad responses.
            data = response.json()
            print("data", data)
            # The API returns the roomId; we rename it to streamId for consistency.
            stream_id = data.get("roomId")
            if stream_id:
                return stream_id
        except Exception as e:
            return str(e)
    def create(self, request, *args, **kwargs):
        user_id = get_body_data(request, "user_id", "").strip()
        title = get_body_data(request, "title", "").strip()
        description = get_body_data(request, "description", "").strip()
        thumbnail = get_body_data(request, "thumbnail", "").strip()
        recording = get_body_data(request, "recording", "").strip()
        is_live = get_body_data(request, "is_live", False)

        _stream_url = self.createStreamid()
        if not _stream_url:
            return api_failed("Stream ID is failed", headers={"code": 1001}).secure().rest()

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return api_failed("User is not valid. Registration is required", headers={"code": 1001}).secure().rest()
        if not thumbnail:
            return api_failed("Thumbnail file is required.", headers={"code": 1001}).secure().rest()

        if not title or not description or not thumbnail:
            return api_failed("Title and description and thumbnail are required.", headers={"code": 1001}).secure().rest()
        if is_live:
            current_time = timezone.now()
            try:
                livestream = LiveStream.objects.create(
                    user=user,
                    title=title,
                    description=description,
                    thumbnail=thumbnail,
                    stream_id=_stream_url,
                    is_live=True,
                    started_at=current_time

                )
                if thumbnail:
                    thumbnail_path = save_image(thumbnail, image_directory='thumbnail')
                    livestream.thumbnail = thumbnail_path
                    livestream.save()
                serialized = self.get_serializer(livestream, context={"request": request}).data
                return api_success("Live stream created successfully.", body={"livestream": serialized}).secure().rest()
            except Exception as e:
                import traceback
                traceback.print_exc()
                return api_failed("Error occurred while creating live stream.", headers={"code": 1002}).secure().rest()
        else:
            return api_success("Live stream created successfully.", body={"livestream": ""}).secure().rest()

class GetLiveStreamListView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Fetch a list of live streams (can be filtered by live/recorded status).
    """
    queryset = LiveStream.objects.all()
    serializer_class = LiveStreamSerializer

    def create(self, request, *args, **kwargs):
        # Parameter: live_only = "true" or "false"
        live_only = get_body_data(request, "live_only", "true").strip().lower() == "true"
        try:
            if live_only:
                streams = LiveStream.objects.filter(is_live=True)
            else:
                streams = LiveStream.objects.all()
            serialized = self.get_serializer(streams, many=True, context={"request": request}).data
            return api_success("Live streams fetched successfully.", body={"livestreams": serialized}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while fetching live streams.", headers={"code": 1003}).secure().rest()


class UpdateLiveStreamView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Update a live stream (e.g., mark as ended and save the recording).
    """
    queryset = LiveStream.objects.all()
    serializer_class = LiveStreamSerializer

    def create(self, request, *args, **kwargs):
        livestream_id = get_body_data(request, "livestream_id", "").strip()
        recording = request.FILES.get("recording", None)  # File upload for recording

        if not livestream_id:
            return api_failed("Live stream ID is required.", headers={"code": 1001}).secure().rest()

        try:
            livestream = get_object_or_404(LiveStream, id=livestream_id)
            # Mark as ended and update recording if provided
            livestream.is_live = False
            livestream.ended_at = timezone.now()
            if recording:
                livestream.recording = recording
            livestream.save()
            serialized = self.get_serializer(livestream, context={"request": request}).data
            return api_success("Live stream updated successfully.", body={"livestream": serialized}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while updating live stream.", headers={"code": 1002}).secure().rest()

# -------------------------------
# LiveStream Comment Views
# -------------------------------
class CreateLiveStreamCommentView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Create a comment on a live stream.
    """
    queryset = LiveStreamComment.objects.all()
    serializer_class = LiveStreamCommentSerializer

    def create(self, request, *args, **kwargs):
        livestream_id = get_body_data(request, "livestream_id", "").strip()
        comment_text = get_body_data(request, "comment", "").strip()
        user = request.user  # Use authenticated user; allow None for guest if needed

        if not livestream_id or not comment_text:
            return api_failed("Live stream ID and comment are required.", headers={"code": 1001}).secure().rest()

        try:
            livestream = get_object_or_404(LiveStream, id=livestream_id)
            comment = LiveStreamComment.objects.create(
                livestream=livestream,
                user=user if user.is_authenticated else None,
                comment=comment_text
            )
            serialized = self.get_serializer(comment, context={"request": request}).data
            return api_success("Comment added successfully.", body={"comment": serialized}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while adding comment.", headers={"code": 1002}).secure().rest()


# -------------------------------
# Story Views
# -------------------------------
class GetActiveStoriesView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    API endpoint to fetch all live (active) stories that are not expired,
    sorted so that unseen and new stories come first.
    """
    queryset = Story.objects.all()
    serializer_class = StorySerializer

    def create(self, request, *args, **kwargs):
        try:
            # Read the filter flag from request (e.g., "active")
            filter_flag = get_body_data(request, "filter", "").strip()
            current_time = timezone.now()

            # Filter stories that have not expired.
            qs = Story.objects.filter(expires_at__gt=current_time)
            # Optionally, use filter_flag here if needed (currently "active" is assumed)

            # If the user is authenticated, annotate and order by unseen status and creation time.
            if request.user and request.user.is_authenticated:
                qs = qs.annotate(
                    is_unseen=Case(
                        When(viewers__pk=request.user.pk, then=Value(False)),
                        default=Value(True),
                        output_field=BooleanField()
                    )
                ).order_by("-is_unseen", "-created_at")
            else:
                qs = qs.order_by("-created_at")

            serialized_stories = self.get_serializer(
                qs, many=True, context={"request": request}
            ).data

            return api_success("Active stories fetched successfully.",
                               body={"stories": serialized_stories}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while fetching active stories.",
                              headers={"code": 1001}).secure().rest()


class MarkStoryViewedView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    API endpoint to mark a story as viewed by a user.
    """
    queryset = Story.objects.all()
    serializer_class = StorySerializer  # Optional if you want to return story data

    def create(self, request, *args, **kwargs):
        try:
            story_id = get_body_data(request, "story_id", "")
            user_id = get_body_data(request, "user_id", "").strip()

            if not story_id or not user_id:
                return api_failed("story_id and user_id are required", headers={"code": 1001}).secure().rest()

            story = get_object_or_404(Story, id=story_id)
            user = get_object_or_404(User, user_id=user_id)

            if not story.viewers.filter(pk=user.pk).exists():
                story.viewers.add(user)

            views_count = story.viewers.count()
            return api_success("Story marked as viewed.", body={"views_count": views_count}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error marking story as viewed.", headers={"code": 1002}).secure().rest()

class MarkStoryLikedView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    API endpoint to toggle like status for a story.
    """
    queryset = Story.objects.all()
    serializer_class = StorySerializer  # Optional if you want to return story data

    def create(self, request, *args, **kwargs):
        try:
            story_id = get_body_data(request, "story_id", "")
            user_id = get_body_data(request, "user_id", "").strip()

            if not story_id or not user_id:
                return api_failed("story_id and user_id are required", headers={"code": 1001}).secure().rest()

            story = get_object_or_404(Story, id=story_id)
            user = get_object_or_404(User, user_id=user_id)

            # Toggle like: if user already liked it, remove the like; otherwise, add it.
            if story.likes.filter(pk=user.pk).exists():
                story.likes.remove(user)
                is_liked = False
            else:
                story.likes.add(user)
                is_liked = True

            likes_count = story.likes.count()
            return api_success("Story like status updated.", body={"likes_count": likes_count, "is_liked": is_liked}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error updating like status.", headers={"code": 1002}).secure().rest()


class CreateStoryView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Create a new story.
    """
    queryset = Story.objects.all()
    serializer_class = StorySerializer

    def create(self, request, *args, **kwargs):
        # Retrieve encrypted metadata from request.data (for multipart, middleware sets these fields in request.data)
        caption = get_body_data(request, "caption", "")
        user_id = get_body_data(request, "user_id", "")
        media = get_body_data(request, "media", "")

        print(caption, user_id)

        if not media:
            return api_failed("Media file is required.", headers={"code": 1001}).secure().rest()

        try:
            # Retrieve the user object using the custom user_id field
            user = User.objects.get(user_id=user_id)
        except Exception as e:
            traceback.print_exc()
            return api_failed("User not found.", headers={"code": 1004}).secure().rest()

        current_time = timezone.now()
        next_day_time = current_time + timedelta(days=1)
        try:
            # Create the story. Optionally, convert expires_at to a datetime if necessary.
            story = Story.objects.create(
                user=user,
                media=media,
                caption=caption,
                expires_at=next_day_time
            )
            if media:
                video_path = save_video(media, video_directory='stories')
                story.media = video_path
                story.save()
            serialized = self.get_serializer(story, context={"request": request}).data
            return api_success("Story created successfully.", body={"story": serialized}).secure().rest()
        except Exception as e:
            traceback.print_exc()
            return api_failed("Error occurred while creating story.", headers={"code": 1002}).secure().rest()

# -------------------------------
# User Follow Views
# -------------------------------

class UserFollowView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    Follow or unfollow a user.
    """
    queryset = UserFollow.objects.all()
    serializer_class = UserFollowSerializer

    def create(self, request, *args, **kwargs):
        # Expect 'target_user_id' in the request body
        target_user_id = get_body_data(request, "target_user_id", "").strip()
        user = request.user

        if not target_user_id:
            return api_failed("Target user ID is required.", headers={"code": 1001}).secure().rest()

        try:
            target_user = get_object_or_404(User, id=target_user_id)
            # Check if the follow relation exists
            follow_relation = UserFollow.objects.filter(follower=user, following=target_user).first()
            if follow_relation:
                # Unfollow if relation exists
                follow_relation.delete()
                return api_success("Unfollowed successfully.", body={"following": False}).secure().rest()
            else:
                # Create follow relation
                follow_relation = UserFollow.objects.create(follower=user, following=target_user)
                serialized = self.get_serializer(follow_relation, context={"request": request}).data
                return api_success("Followed successfully.", body={"following": True, "relation": serialized}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while processing follow request.", headers={"code": 1002}).secure().rest()


class CreateStreamIdView(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = LiveStream.objects.all()
    serializer_class = LiveStreamSerializer

    def create(self, request, *args, **kwargs):
        user_id = get_body_data(request, 'user_id', default='').strip()
        token = get_body_data(request, "token", "").strip()
        try:
            url = "https://api.videosdk.live/v2/rooms"
            headers = {
                "authorization": token,
                "Content-Type": "application/json",
            }
            response = requests.post(url, headers=headers, json={})
            response.raise_for_status()  # Raises an error for bad responses.
            data = response.json()
            print("data", data)
            # The API returns the roomId; we rename it to streamId for consistency.
            stream_id = data.get("roomId")
            link = data.get('links')
            get_room = link.get('get_room')

            print("get_room",get_room)
            if not stream_id:
                raise ValueError("Stream ID not found in response")

            return api_success("Got the Meeting id.", body={ "roomId": stream_id,
                "get_room":get_room}).secure().rest()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_failed("Error occurred while processing follow request.", headers={"code": 1002}).secure().rest()