# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
# modified for an Audio skill
# John Allwork
# 20 April 2021
# refernce: https://developer.amazon.com/en-US/docs/alexa/custom-skills/audioplayer-interface-reference.html
#
# test              expected
#   play my music   starts from track 0
#   next            plays next track
#   previous         plays previous track
#   startOver        plays current track from beginning
#   pause / resume  paused and resumes from where left off
#  
#   leave play to end track - next track plays
#   then repeat above tests (next previous startover)
#   leave to end of music - start from beginning?

import os
import boto3
import track_info as trackInfo

from ask_sdk_dynamodb.adapter import DynamoDbAdapter

import logging
import ask_sdk_core.utils as ask_utils

from utils import create_presigned_url

from ask_sdk_core.dispatch_components import AbstractRequestInterceptor
from ask_sdk_core.dispatch_components import AbstractResponseInterceptor

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from ask_sdk_core.utils import is_intent_name
from ask_sdk_core.utils import get_intent_name
from ask_sdk_core.utils import is_request_type
from ask_sdk_model.ui import StandardCard, Image, SimpleCard
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective, PlayBehavior, AudioItem, Stream, AudioItemMetadata,
    StopDirective)
from ask_sdk_model.interfaces import display

ddb_region = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
ddb_table_name = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')

ddb_resource = boto3.resource('dynamodb', region_name=ddb_region)
dynamodb_adapter = DynamoDbAdapter(table_name=ddb_table_name, create_table=False, dynamodb_resource=ddb_resource)

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_dynamodb.adapter import DynamoDbAdapter

small_image_url = create_presigned_url("Media/Note108.png")
large_image_url = create_presigned_url("Media/Note512.png")


audio_data = {
    "card": {
        "title": 'My music',
        "text": 'I like music',
    }
}
card = StandardCard(
    title=audio_data["card"]["title"],
    text=audio_data["card"]["text"],
    image=Image(
        small_image_url=small_image_url,
        large_image_url=large_image_url
    )
)

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hello, I can play your music, just say play my music"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
    
class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Just say play my music"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class AudioPlayIntentHandler(AbstractRequestHandler):
    # Handler for Audioplayer Play Intent and RESUME
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("PlayAudio")(handler_input) or
                is_intent_name("AMAZON.ResumeIntent")(handler_input))

        
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("in AudioPlayIntent")
        persistence_attr = handler_input.attributes_manager.persistent_attributes

        if (is_intent_name("PlayAudio")(handler_input)):
            logger.info("play Audio")
            # first time - set track to zero
            track_number = 0
            persistence_attr["track_number"] = track_number
            
            card = StandardCard(
                title=trackInfo.track_info[track_number]["title"],
                text=trackInfo.track_info[track_number]["artist"],
                image=Image(
                    small_image_url=small_image_url,
                    large_image_url=large_image_url
                    )
                )

            audio_key = trackInfo.track_info[track_number]["url"]
            audio_url = create_presigned_url(audio_key)
            persistence_attr["playback_settings"]["url"] = audio_url
            persistence_attr["playback_settings"]["token"] = audio_key
            persistence_attr["playback_settings"]["offset_in_milliseconds"] = 0
            persistence_attr["playback_settings"]["next_stream_enqueued"] = False
            
            speech_text = "Playing your music"
            directive = PlayDirective(
                play_behavior=PlayBehavior.REPLACE_ALL,
                audio_item=AudioItem(
                    stream=Stream(
                        token=audio_key,
                        url=audio_url,
                        offset_in_milliseconds=0,
                        expected_previous_token=None),
                    metadata=None))
            handler_input.response_builder.speak(speech_text).set_card(card).add_directive(directive).set_should_end_session(True)        
        
        else:
            # resume
            logger.info("Resume")
            track_number = int(persistence_attr["track_number"])
            
            audio_key = trackInfo.track_info[track_number]["url"]
            audio_url = create_presigned_url(audio_key)
            persistence_attr["playback_settings"]["url"] = audio_url
            persistence_attr["playback_settings"]["token"] = audio_key
            
            card = StandardCard(
                title=trackInfo.track_info[track_number]["title"],
                text=trackInfo.track_info[track_number]["artist"],
                image=Image(
                    small_image_url=small_image_url,
                    large_image_url=large_image_url
                    )
                )

            directive = PlayDirective(
                play_behavior=PlayBehavior.REPLACE_ALL,
                audio_item=AudioItem(
                    stream=Stream(
                        token=audio_key,
                        url=audio_url,
                        offset_in_milliseconds=persistence_attr["playback_settings"]["offset_in_milliseconds"],
                        expected_previous_token=None),
                    metadata=None))

            handler_input.response_builder.set_card(card).add_directive(directive).set_should_end_session(True)
            
        handler_input.attributes_manager.persistent_attributes = persistence_attr
        return handler_input.response_builder.response


class AudioStopIntentHandler(AbstractRequestHandler):
    # Handler for Stop – come here on pause or cancel too
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input) or
                is_intent_name("AMAZON.PauseIntent")(handler_input))
                
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("in AudioStopIntent")
        speech_text = "Paused"
        # Note when your skill is playing audio, utterances such as 'stop' send your skill an AMAZON.PauseIntent instead of an AMAZON.StopIntent
        # so you can't easily just say goodbye when user says 'stop'
        
        directive = StopDirective()
        # this causes PlaybackStopped request which saves current offset

        handler_input.response_builder.speak(speech_text).add_directive(directive).set_should_end_session(True)
        return handler_input.response_builder.response

# ########## AUDIOPLAYER INTERFACE HANDLERS #########################
# from https://github.com/alexa/skill-sample-python-audio-player
# This section contains handlers related to Audioplayer interface

class PlaybackStartedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackStarted Directive received.
    Confirming that the requested audio file began playing.
    Do not send any specific response.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return  is_request_type("AudioPlayer.PlaybackStarted")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackStartedHandler")
        

        return handler_input.response_builder.response

class PlaybackFinishedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackFinished Directive received.
    Sent when the stream Alexa is playing comes to an end on its own.
    Note: You can't send a new Play directive from here.
    The response cannot include any standard properties such as outputSpeech, card, or reprompt.
    Any other AudioPlayer directives. or Any other directives from other interfaces, such a Dialog directive.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return  is_request_type("AudioPlayer.PlaybackFinished")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackFinishedHandler")
        # reset any attributes? e.g.
        persistence_attr = handler_input.attributes_manager.persistent_attributes
        if persistence_attr["playback_settings"]["next_stream_enqueued"] == True:
            # track ended naturally, enqueued so stored track_number is wrong.
            persistence_attr["playback_settings"]["next_stream_enqueued"] = False
            track_number = int(persistence_attr["track_number"])
            next_track = (track_number  + 1) % len(trackInfo.track_info)
            persistence_attr["track_number"] = next_track
            
        handler_input.attributes_manager.persistent_attributes = persistence_attr

        return handler_input.response_builder.response

class PlaybackStoppedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackStopped Directive received.
    Save playback for resume
    Response example is
    {
      "type": "AudioPlayer.PlaybackStopped",
      "requestId": "unique.id.for.the.request",
      "timestamp": "timestamp of request in format: 2018-04-11T15:15:25Z",
      "token": "token representing the currently playing stream",
      "offsetInMilliseconds": offset in milliseconds,
      "locale": "a locale code such as en-US"
    }
    """
    
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackStopped")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackStoppedHandler")

        #  Save playback info: token, index, offset_in_milliseconds for Resume

        persistence_attr = handler_input.attributes_manager.persistent_attributes
        #track_number = int(persistence_attr["track_number"])
        persistence_attr["playback_settings"]["offset_in_milliseconds"] = handler_input.request_envelope.request.offset_in_milliseconds
        #persistence_attr["playback_settings"]["token"] = trackInfo.track_info[track_number]["url"]
        #persistence_attr["playback_settings"]["url"] = trackInfo.track_info[track_number]["url"]
        # track_number already saved
        handler_input.attributes_manager.persistent_attributes = persistence_attr
        
        return handler_input.response_builder.response


class PlaybackNearlyFinishedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackNearlyFinished Directive received.
    # respond to this request with a Play directive for the next stream and set ENQUEUE
    # https://developer.amazon.com/en-US/docs/alexa/custom-skills/audioplayer-interface-reference.html#playbacknearlyfinished
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackNearlyFinished")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackNearlyFinishedHandler")
        persistence_attr = handler_input.attributes_manager.persistent_attributes
        track_number = int(persistence_attr["track_number"])
        next_track = (track_number  + 1) % len(trackInfo.track_info)
        previous_token = persistence_attr["playback_settings"]["token"] 
        # this the previous token for the next track, i.e. at the moment - it's the current one
        # see https://developer.amazon.com/en-US/docs/alexa/custom-skills/audioplayer-interface-reference.html#playlist-progression
        
        track_number = next_track # for consistency

        audio_key = trackInfo.track_info[track_number]["url"]
        audio_url = create_presigned_url(audio_key)

        persistence_attr["playback_settings"]["offset_in_milliseconds"] = 0
        persistence_attr["playback_settings"]["token"] = audio_key
        persistence_attr["playback_settings"]["url"] = audio_url
        # if i update persistence_attr["track_number"] here, then start over (and resume and play?) picks up wrong track (the next one)
        # if not how does the next track know what to play after automatically playing next track from enqueue?        
        # persistence_attr["track_number"] = track_number
        persistence_attr["playback_settings"]["next_stream_enqueued"] = True
        # check this in playbackfinished. If true, then increment next track
        
        handler_input.attributes_manager.persistent_attributes = persistence_attr
        
        directive = PlayDirective(
            play_behavior=PlayBehavior.ENQUEUE,
            audio_item=AudioItem(
                stream=Stream(
                    token=audio_key,
                    url=audio_url,
                    offset_in_milliseconds=0,
                    expected_previous_token=previous_token),
                metadata=None))     
        # but next track will have new url, but track_number will be wrong
        
        handler_input.response_builder.add_directive(directive).set_should_end_session(True)
        
        return handler_input.response_builder.response

class PlaybackFailedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackFailed Directive received.
    Logging the error and stoprestarting playing with no output speech and card.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackFailed")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        request = handler_input.request_envelope.request
        logger.info("Playback failed: {}".format(request.error))

        return handler_input.response_builder.response

class ExceptionEncounteredHandler(AbstractRequestHandler):
    """Handler to handle exceptions from responses sent by AudioPlayer
    request.
    """
    def can_handle(self, handler_input):
        # type; (HandlerInput) -> bool
        return is_request_type("System.ExceptionEncountered")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("\n**************** EXCEPTION *******************")
        logger.info(handler_input.request_envelope)
        return handler_input.response_builder.response

class NextPlaybackHandler(AbstractRequestHandler):
    """
    Handles Next Intent
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.NextIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In NextPlaybackHandler, track number")
        persistence_attr = handler_input.attributes_manager.persistent_attributes
        track_number = int(persistence_attr["track_number"])
        logger.info(track_number)
        next_track = (track_number  + 1) % len(trackInfo.track_info)
        persistence_attr["track_number"] = next_track
        track_number = next_track # for consistency below
        
        audio_key = trackInfo.track_info[track_number]["url"]
        audio_url = create_presigned_url(audio_key) 
        persistence_attr["playback_settings"]["offset_in_milliseconds"] = 0
        persistence_attr["playback_settings"]["url"] = audio_url
        persistence_attr["playback_settings"]["token"] = audio_key
        persistence_attr["playback_settings"]["next_stream_enqueued"] = False
        
        handler_input.attributes_manager.persistent_attributes = persistence_attr
        
        card = StandardCard(
            title=trackInfo.track_info[track_number]["title"],
            text=trackInfo.track_info[track_number]["artist"],
            image=Image(
                small_image_url=small_image_url,
                large_image_url=large_image_url
                )
            )
        
        directive = PlayDirective(
            play_behavior=PlayBehavior.REPLACE_ALL,
            audio_item=AudioItem(
                stream=Stream(
                    token=audio_key,
                    url=audio_url,
                    offset_in_milliseconds=0,
                    expected_previous_token=None),
                metadata=None))

        handler_input.response_builder.set_card(card).add_directive(directive).set_should_end_session(True)
        return handler_input.response_builder.response

class PreviousPlaybackHandler(AbstractRequestHandler):
    """
    Handler for Playing previous 
    if already at first track, it just stays there
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.PreviousIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PreviousPlaybackHandler")
        persistence_attr = handler_input.attributes_manager.persistent_attributes
        track_number = int(persistence_attr["track_number"])
        next_track = track_number -1
        if (next_track) <0:
            next_track = 0

        persistence_attr["track_number"] = next_track
        track_number = next_track # for consistency below
        audio_key = trackInfo.track_info[track_number]["url"]
        audio_url = create_presigned_url(audio_key) 
        persistence_attr["playback_settings"]["offset_in_milliseconds"] = 0
        persistence_attr["playback_settings"]["url"] = audio_url
        persistence_attr["playback_settings"]["token"] = audio_key
        
        persistence_attr["playback_settings"]["next_stream_enqueued"] = False
        # REPLACE_ALL - replace current and enqueued streams

        card = StandardCard(
            title=trackInfo.track_info[track_number]["title"],
            text=trackInfo.track_info[track_number]["artist"],
            image=Image(
                small_image_url=small_image_url,
                large_image_url=large_image_url
                )
            )
        
        handler_input.attributes_manager.persistent_attributes = persistence_attr

        directive = PlayDirective(
            play_behavior=PlayBehavior.REPLACE_ALL,
            audio_item=AudioItem(
                stream=Stream(
                    token=audio_key,
                    url=audio_url,
                    offset_in_milliseconds=0,
                    expected_previous_token=None),
                metadata=None))

        handler_input.response_builder.set_card(card).add_directive(directive).set_should_end_session(True)        
        
        return handler_input.response_builder.response

class StartOverHandler(AbstractRequestHandler):
    """Handler for start over."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.StartOverIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # go to beginning of track
        logger.info("In StartOverHandler")
        persistence_attr = handler_input.attributes_manager.persistent_attributes
        track_number = int(persistence_attr["track_number"])

        audio_key = trackInfo.track_info[track_number]["url"]
        audio_url = create_presigned_url(audio_key) 
        persistence_attr["playback_settings"]["offset_in_milliseconds"] = 0
        persistence_attr["playback_settings"]["url"] = audio_url
        persistence_attr["playback_settings"]["token"] = audio_key
        
        persistence_attr["playback_settings"]["next_stream_enqueued"] = False
        
        handler_input.attributes_manager.persistent_attributes = persistence_attr
        
        card = StandardCard(
            title=trackInfo.track_info[track_number]["title"],
            text=trackInfo.track_info[track_number]["artist"],
            image=Image(
                small_image_url=small_image_url,
                large_image_url=large_image_url
                )
            )
        
        directive = PlayDirective(
            play_behavior=PlayBehavior.REPLACE_ALL,
            audio_item=AudioItem(
                stream=Stream(
                    token=audio_key,
                    url=audio_url,
                    offset_in_milliseconds=0,
                    expected_previous_token=None),
                metadata=None))

        handler_input.response_builder.set_card(card).add_directive(directive).set_should_end_session(True)
        
        return handler_input.response_builder.response
    
# ###################################################################

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("in SessionEnded")

        # Any cleanup logic goes here.

        return handler_input.response_builder.response

class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )

class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)
        logger.info("exception")
        logger.info(exception)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# ###################  INTERCEPTORS  ############################ 

class LoadPersistenceAttributesRequestInterceptor(AbstractRequestInterceptor):
    #Check if user is invoking skill for first time and initialize preset
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        #handler_input.attributes_manager.delete_persistent_attributes()
        
        persistence_attr = handler_input.attributes_manager.persistent_attributes
        
        if len(persistence_attr) == 0:
            logger.info("Create attributes")
            # First time skill user
            persistence_attr["playback_settings"] = {
                "token": None,
                "offset_in_milliseconds": 0,
                "url" : None,
                "next_stream_enqueued" : False
            }
            
            persistence_attr["track_number"] = 0

        else:
            # Convert decimals to integers, because of AWS SDK DynamoDB issue
            # https://github.com/boto/boto3/issues/369
            pass

        
        return    

class SavePersistenceAttributesResponseInterceptor(AbstractResponseInterceptor):
    #Save persistence attributes before sending response to user.
    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        
        handler_input.attributes_manager.persistent_attributes = persistence_attr
        handler_input.attributes_manager.save_persistent_attributes()
        
        return

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

sb = SkillBuilder()

sb = CustomSkillBuilder(persistence_adapter = dynamodb_adapter)

# Interceptors
sb.add_global_request_interceptor(LoadPersistenceAttributesRequestInterceptor())
sb.add_global_response_interceptor(SavePersistenceAttributesResponseInterceptor())

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(AudioPlayIntentHandler())
sb.add_request_handler(AudioStopIntentHandler())
sb.add_request_handler(NextPlaybackHandler())
sb.add_request_handler(PreviousPlaybackHandler())
sb.add_request_handler(StartOverHandler())


# ########## AUDIOPLAYER INTERFACE HANDLERS #########################
sb.add_request_handler(PlaybackStartedHandler())
sb.add_request_handler(PlaybackFinishedHandler())
sb.add_request_handler(PlaybackStoppedHandler())
sb.add_request_handler(PlaybackNearlyFinishedHandler())
sb.add_request_handler(PlaybackFailedHandler())
sb.add_request_handler(ExceptionEncounteredHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
