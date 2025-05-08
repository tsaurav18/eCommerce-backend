
import os
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from consultantapi import views_files
from ecombackend import settings

router = SimpleRouter()
router.register('get_csrf', views_files.GetCsrfView, basename='get_csrf')
router.register('get_courses', views_files.CourseListView, basename='get_courses')

router.register('course_enroll', views_files.EnrollCourseView, basename='course_enroll')
router.register('check_course_enroll', views_files.CheckEnrollCourseView, basename='check_course_enroll')
router.register('course_payment', views_files.CoursePaymentView, basename='course_payment')
router.register('course_user_detail', views_files.UserDetailView, basename='course_user_detail')
router.register('get_course_videos', views_files.CourseVideoListView, basename='get_course_videos')

router.register('course_register', views_files.CourseRegisterView, basename='course_register')
router.register('course_login', views_files.CourseLoginView, basename='course_login')
router.register('course_send_otp', views_files.CourseSendOtpView, basename='course_send_otp')
router.register('course_verify_otp', views_files.CourseVerifyOtpView, basename='course_verify_otp')
router.register('course_google_login', views_files.CourseGoogleLoginView, basename='course_google_login')
router.register('total_learners', views_files.TotalLearnersView, basename='total_learners')

router.register('create_contact_request', views_files.CreateContactMessageView, basename='create_contact_request')
router.register('create_course_contact', views_files.CreateCoursesContactView, basename='create_course_contact')

router.register('book_visa_package', views_files.BookVisaPackageView, basename="book_package")
router.register('get_visa_services_list', views_files.GetVisaServiceListView, basename="get_visa_services_list")

router.register('get_visa_package_details', views_files.GetVisaPackageDetailsView, basename="get_visa_package_details")
urlpatterns = [
    path('', include(router.urls))
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)