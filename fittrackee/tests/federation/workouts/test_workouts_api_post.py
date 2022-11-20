import json
import os
from io import BytesIO
from unittest.mock import Mock, call, patch

import pytest
from flask import Flask

from fittrackee.privacy_levels import PrivacyLevel
from fittrackee.tests.utils import generate_follow_request
from fittrackee.users.models import FollowRequest, User
from fittrackee.workouts.constants import WORKOUT_DATE_FORMAT
from fittrackee.workouts.models import Sport

from ...mixins import ApiTestCaseMixin


@patch('fittrackee.workouts.workouts.send_to_remote_inbox')
class TestFederationPostWorkoutWithoutGpx(ApiTestCaseMixin):
    def test_it_does_not_call_sent_to_inbox_if_user_has_no_remote_followers(
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        user_2: User,
        sport_1_cycling: Sport,
        follow_request_from_user_2_to_user_1: FollowRequest,
    ) -> None:
        user_1.approves_follow_request_from(user_2)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts/no_gpx',
            content_type='application/json',
            data=json.dumps(
                dict(
                    sport_id=1,
                    duration=3600,
                    workout_date='2018-05-15 14:05',
                    distance=10,
                    workout_visibility=PrivacyLevel.FOLLOWERS_AND_REMOTE.value,
                )
            ),
            headers=dict(Authorization=f'Bearer {auth_token}'),
        )

        send_to_remote_inbox_mock.send.assert_not_called()

    def test_it_does_not_call_sent_to_inbox_if_privacy_is_local_followers_only(
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user: User,
        sport_1_cycling: Sport,
        follow_request_from_remote_user_to_user_1: FollowRequest,
    ) -> None:
        user_1.approves_follow_request_from(remote_user)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts/no_gpx',
            content_type='application/json',
            data=json.dumps(
                dict(
                    sport_id=1,
                    duration=3600,
                    workout_date='2018-05-15 14:05',
                    distance=10,
                    workout_visibility=PrivacyLevel.FOLLOWERS.value,
                )
            ),
            headers=dict(Authorization=f'Bearer {auth_token}'),
        )

        send_to_remote_inbox_mock.send.assert_not_called()

    def test_it_does_not_call_sent_to_inbox_if_workout_is_private(
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user: User,
        sport_1_cycling: Sport,
        follow_request_from_remote_user_to_user_1: FollowRequest,
    ) -> None:
        user_1.approves_follow_request_from(remote_user)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts/no_gpx',
            content_type='application/json',
            data=json.dumps(
                dict(
                    sport_id=1,
                    duration=3600,
                    workout_date=self.get_date_string(
                        date_format=WORKOUT_DATE_FORMAT
                    ),
                    distance=10,
                    workout_visibility=PrivacyLevel.PRIVATE.value,
                )
            ),
            headers=dict(Authorization=f'Bearer {auth_token}'),
        )

        send_to_remote_inbox_mock.send.assert_not_called()

    @pytest.mark.parametrize(
        'workout_visibility',
        [
            PrivacyLevel.FOLLOWERS_AND_REMOTE,
            PrivacyLevel.PUBLIC,
        ],
    )
    def test_it_calls_sent_to_inbox_if_user_has_follower_from_remote_fittrackee_instance(  # noqa
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user: User,
        sport_1_cycling: Sport,
        follow_request_from_remote_user_to_user_1: FollowRequest,
        workout_visibility: PrivacyLevel,
    ) -> None:
        user_1.approves_follow_request_from(remote_user)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts/no_gpx',
            content_type='application/json',
            data=json.dumps(
                dict(
                    sport_id=1,
                    duration=3600,
                    workout_date=self.get_date_string(
                        date_format=WORKOUT_DATE_FORMAT
                    ),
                    distance=10,
                    workout_visibility=workout_visibility.value,
                )
            ),
            headers=dict(Authorization=f'Bearer {auth_token}'),
        )

        workout_activity, _ = user_1.workouts[0].get_activities()
        send_to_remote_inbox_mock.send.assert_called_once_with(
            sender_id=user_1.actor.id,
            activity=workout_activity,
            recipients=[remote_user.actor.shared_inbox_url],
        )

    @pytest.mark.parametrize(
        'workout_visibility',
        [
            PrivacyLevel.FOLLOWERS_AND_REMOTE,
            PrivacyLevel.PUBLIC,
        ],
    )
    def test_it_calls_sent_to_inbox_if_user_has_follower_from_remote_other_instance(  # noqa
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user_2: User,
        sport_1_cycling: Sport,
        workout_visibility: PrivacyLevel,
    ) -> None:
        generate_follow_request(remote_user_2, user_1)
        user_1.approves_follow_request_from(remote_user_2)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts/no_gpx',
            content_type='application/json',
            data=json.dumps(
                dict(
                    sport_id=1,
                    duration=3600,
                    workout_date='2018-05-15 14:05',
                    distance=10,
                    workout_visibility=workout_visibility.value,
                )
            ),
            headers=dict(Authorization=f'Bearer {auth_token}'),
        )

        _, note_activity = user_1.workouts[0].get_activities()
        send_to_remote_inbox_mock.send.assert_called_once_with(
            sender_id=user_1.actor.id,
            activity=note_activity,
            recipients=[remote_user_2.actor.shared_inbox_url],
        )


@patch('fittrackee.workouts.workouts.send_to_remote_inbox')
class TestFederationPostWorkoutWithGpx(ApiTestCaseMixin):
    def test_it_does_not_call_sent_to_inbox_if_user_has_no_remote_followers(
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        user_2: User,
        sport_1_cycling: Sport,
        follow_request_from_user_2_to_user_1: FollowRequest,
        gpx_file: str,
    ) -> None:
        user_1.approves_follow_request_from(user_2)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts',
            data=dict(
                file=(BytesIO(str.encode(gpx_file)), 'example.gpx'),
                data=(
                    f'{{"sport_id": 1, "map_visibility": '
                    f'"{PrivacyLevel.FOLLOWERS.value}", '
                    f'"workout_visibility": '
                    f'"{PrivacyLevel.FOLLOWERS_AND_REMOTE.value}"}}'
                ),
            ),
            headers=dict(
                content_type='multipart/form-data',
                Authorization=f'Bearer {auth_token}',
            ),
        )

        send_to_remote_inbox_mock.send.assert_not_called()

    def test_it_does_not_call_sent_to_inbox_if_privacy_is_local_followers_only(
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user: User,
        sport_1_cycling: Sport,
        follow_request_from_remote_user_to_user_1: FollowRequest,
        gpx_file: str,
    ) -> None:
        user_1.approves_follow_request_from(remote_user)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts',
            data=dict(
                file=(BytesIO(str.encode(gpx_file)), 'example.gpx'),
                data=(
                    f'{{"sport_id": 1, "map_visibility": '
                    f'"{PrivacyLevel.FOLLOWERS.value}", '
                    f'"workout_visibility": '
                    f'"{PrivacyLevel.FOLLOWERS.value}"}}'
                ),
            ),
            headers=dict(
                content_type='multipart/form-data',
                Authorization=f'Bearer {auth_token}',
            ),
        )

        send_to_remote_inbox_mock.send.assert_not_called()

    def test_it_does_not_call_sent_to_inbox_if_workout_is_private(
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user: User,
        sport_1_cycling: Sport,
        follow_request_from_remote_user_to_user_1: FollowRequest,
        gpx_file: str,
    ) -> None:
        user_1.approves_follow_request_from(remote_user)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts',
            data=dict(
                file=(BytesIO(str.encode(gpx_file)), 'example.gpx'),
                data=(
                    f'{{"sport_id": 1, "map_visibility": '
                    f'"{PrivacyLevel.PRIVATE.value}", '
                    f'"workout_visibility": '
                    f'"{PrivacyLevel.PRIVATE.value}"}}'
                ),
            ),
            headers=dict(
                content_type='multipart/form-data',
                Authorization=f'Bearer {auth_token}',
            ),
        )

        send_to_remote_inbox_mock.send.assert_not_called()

    def test_it_calls_sent_to_inbox_if_user_has_follower_from_remote_fittrackee_instance(  # noqa
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user: User,
        sport_1_cycling: Sport,
        follow_request_from_remote_user_to_user_1: FollowRequest,
        gpx_file: str,
    ) -> None:
        user_1.approves_follow_request_from(remote_user)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts',
            data=dict(
                file=(BytesIO(str.encode(gpx_file)), 'example.gpx'),
                data=(
                    f'{{"sport_id": 1, "map_visibility": '
                    f'"{PrivacyLevel.PRIVATE.value}", '
                    f'"workout_visibility": '
                    f'"{PrivacyLevel.FOLLOWERS_AND_REMOTE.value}"}}'
                ),
            ),
            headers=dict(
                content_type='multipart/form-data',
                Authorization=f'Bearer {auth_token}',
            ),
        )

        workout_activity, _ = user_1.workouts[0].get_activities()
        send_to_remote_inbox_mock.send.assert_called_once_with(
            sender_id=user_1.actor.id,
            activity=workout_activity,
            recipients=[remote_user.actor.shared_inbox_url],
        )

    def test_it_calls_sent_to_inbox_if_user_has_follower_from_remote_other_instance(  # noqa
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user_2: User,
        sport_1_cycling: Sport,
        gpx_file: str,
    ) -> None:
        generate_follow_request(remote_user_2, user_1)
        user_1.approves_follow_request_from(remote_user_2)
        client, auth_token = self.get_test_client_and_auth_token(
            app_with_federation, user_1.email
        )

        client.post(
            '/api/workouts',
            data=dict(
                file=(BytesIO(str.encode(gpx_file)), 'example.gpx'),
                data=(
                    f'{{"sport_id": 1, "map_visibility": '
                    f'"{PrivacyLevel.PRIVATE.value}", '
                    f'"workout_visibility": '
                    f'"{PrivacyLevel.FOLLOWERS_AND_REMOTE.value}"}}'
                ),
            ),
            headers=dict(
                content_type='multipart/form-data',
                Authorization=f'Bearer {auth_token}',
            ),
        )

        _, note_activity = user_1.workouts[0].get_activities()
        send_to_remote_inbox_mock.send.assert_called_once_with(
            sender_id=user_1.actor.id,
            activity=note_activity,
            recipients=[remote_user_2.actor.shared_inbox_url],
        )


@patch('fittrackee.workouts.workouts.send_to_remote_inbox')
class TestFederationPostWorkoutWithZipArchive(ApiTestCaseMixin):
    def test_it_calls_sent_to_inbox_if_user_has_follower_from_remote_fittrackee_instance(  # noqa
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user: User,
        sport_1_cycling: Sport,
        follow_request_from_remote_user_to_user_1: FollowRequest,
    ) -> None:
        user_1.approves_follow_request_from(remote_user)
        # 'gpx_test.zip' contains 3 gpx files (same data) and 1 non-gpx file
        file_path = os.path.join(
            app_with_federation.root_path, 'tests/files/gpx_test.zip'
        )
        with open(file_path, 'rb') as zip_file:
            client, auth_token = self.get_test_client_and_auth_token(
                app_with_federation, user_1.email
            )

            client.post(
                '/api/workouts',
                data=dict(
                    file=(zip_file, 'gpx_test.zip'),
                    data=(
                        f'{{"sport_id": 1, "map_visibility": '
                        f'"{PrivacyLevel.PRIVATE.value}", '
                        f'"workout_visibility": '
                        f'"{PrivacyLevel.FOLLOWERS_AND_REMOTE.value}"}}'
                    ),
                ),
                headers=dict(
                    content_type='multipart/form-data',
                    Authorization=f'Bearer {auth_token}',
                ),
            )

            assert send_to_remote_inbox_mock.send.call_count == 3
            calls = []
            for workout in user_1.workouts:
                workout_activity, _ = workout.get_activities()
                calls.append(
                    call(
                        sender_id=user_1.actor.id,
                        activity=workout_activity,
                        recipients=[remote_user.actor.shared_inbox_url],
                    )
                )
            send_to_remote_inbox_mock.send.assert_has_calls(
                calls, any_order=True
            )

    def test_it_calls_sent_to_inbox_if_user_has_follower_from_remote_other_instance(  # noqa
        self,
        send_to_remote_inbox_mock: Mock,
        app_with_federation: Flask,
        user_1: User,
        remote_user_2: User,
        sport_1_cycling: Sport,
        gpx_file: str,
    ) -> None:
        generate_follow_request(remote_user_2, user_1)
        user_1.approves_follow_request_from(remote_user_2)
        # 'gpx_test.zip' contains 3 gpx files (same data) and 1 non-gpx file
        file_path = os.path.join(
            app_with_federation.root_path, 'tests/files/gpx_test.zip'
        )
        with open(file_path, 'rb') as zip_file:
            client, auth_token = self.get_test_client_and_auth_token(
                app_with_federation, user_1.email
            )

            client.post(
                '/api/workouts',
                data=dict(
                    file=(zip_file, 'gpx_test.zip'),
                    data=(
                        f'{{"sport_id": 1, "map_visibility": '
                        f'"{PrivacyLevel.PRIVATE.value}", '
                        f'"workout_visibility": '
                        f'"{PrivacyLevel.FOLLOWERS_AND_REMOTE.value}"}}'
                    ),
                ),
                headers=dict(
                    content_type='multipart/form-data',
                    Authorization=f'Bearer {auth_token}',
                ),
            )

            assert send_to_remote_inbox_mock.send.call_count == 3
            calls = []
            for workout in user_1.workouts:
                _, note_activity = workout.get_activities()
                calls.append(
                    call(
                        sender_id=user_1.actor.id,
                        activity=note_activity,
                        recipients=[remote_user_2.actor.shared_inbox_url],
                    )
                )
            send_to_remote_inbox_mock.send.assert_has_calls(
                calls, any_order=True
            )