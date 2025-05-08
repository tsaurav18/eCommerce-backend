from rest_framework import serializers

from api.utility_files.api_call import get_body_data
from communityapi.models import *
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('user_id', 'email', 'name', 'register_datetime')
        read_only_fields = ('user_id', 'email', 'name', 'register_datetime')


class LiveStreamSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()
    class Meta:
        model = LiveStream
        fields = '__all__'
        read_only_fields = ('user', 'started_at', 'ended_at')
    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if request and obj.thumbnail:
            return request.build_absolute_uri(obj.thumbnail.url)
        return None

class LiveStreamCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveStreamComment
        fields = '__all__'
        read_only_fields = ('created_at',)

class StorySerializer(serializers.ModelSerializer):
    is_viewed = serializers.SerializerMethodField()
    views_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    # user_details = serializers.SerializerMethodField()
    user_details= UserSerializer(source="user",  read_only=True)
    media = serializers.SerializerMethodField()
    class Meta:
        model = Story
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

    def _get_request_user(self):
        """
        Helper function to obtain the user from request context.
        First, it attempts to use request.user if available and authenticated.
        Otherwise, it falls back to reading 'user_id' from the request data.
        """
        request = self.context.get("request")
        user = None
        if request:
            if hasattr(request, "user") and request.user and request.user.is_authenticated:
                user = request.user
            else:
                # Fallback: attempt to get user_id from request data.
                user_id = get_body_data(request, "user_id", "")
                if user_id:
                    try:
                        user = User.objects.get(user_id=user_id)
                    except User.DoesNotExist:
                        user = None
        return user

    def get_is_viewed(self, obj):
        user = self._get_request_user()
        if user:
            return obj.viewers.filter(pk=user.pk).exists()
        return False

    def get_views_count(self, obj):
        return obj.viewers.count()

    def get_is_liked(self, obj):
        user = self._get_request_user()
        if user:
            return obj.likes.filter(pk=user.pk).exists()
        return False

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_media(self, obj):
        request = self.context.get('request')
        if request and obj.media:
            print("obj.media", obj.media)
            return request.build_absolute_uri(obj.media.url)
        return None



class UserFollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFollow
        fields = '__all__'
        read_only_fields = ('created_at',)