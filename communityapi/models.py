from django.db import models
from api.models import *
# Create your models here.
from django.db import models


class LiveStream(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_streams')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    stream_id = models.TextField(max_length=500, help_text="streamUrl for the live stream source")
    is_live = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    recording = models.FileField(upload_to='media/livestream_recordings/', blank=True, null=True)
    thumbnail = models.FileField(upload_to='media/livestream_thumbnails/', blank=True, null=True)

    def __str__(self):
        return f"{self.title} by {self.user.user_id}"


class LiveStreamComment(models.Model):
    livestream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.user_id if self.user else 'Guest'} on {self.livestream.title}"


class Story(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    media = models.FileField(upload_to='media/stories/', help_text="Image or video file")
    caption = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    viewers = models.ManyToManyField(
        User,
        related_name="viewed_stories",
        blank=True
    )
    # Track which users have liked the story
    likes = models.ManyToManyField(
        User,
        related_name="liked_stories",
        blank=True
    )
    def __str__(self):
        return f"Story by {self.user.user_id}"


class UserFollow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.user_id} follows {self.following.user_id}"
