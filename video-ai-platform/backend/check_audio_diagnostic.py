"""
DIAGNOSTIC: Check if audio_analysis is properly structured for narrative

Run this to see why narrative isn't using audio data
"""

import boto3
import json
import os

# AWS Config
S3_BUCKET = 'video-ai-uploads'
AWS_REGION = 'us-east-2'
VIDEO_ID = '98e8f391-38ba-46ff-9836-dbdbd6f3bfc3'  # Your forest video

s3_client = boto3.client('s3', region_name=AWS_REGION)

def check_audio_in_s3():
    """Check if audio_analysis exists in S3 detections.json"""
    s3_key = f"results/{VIDEO_ID}/detections.json"
    
    try:
        print(f"📥 Fetching from S3: {s3_key}\n")
        s3_response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        data = json.loads(s3_response['Body'].read())
        
        print("✅ S3 DATA STRUCTURE:")
        print(f"   Keys in file: {list(data.keys())}\n")
        
        # Check audio_analysis
        if 'audio_analysis' in data:
            audio = data['audio_analysis']
            print("🎤 AUDIO_ANALYSIS FOUND!")
            print(f"   Keys: {list(audio.keys())}\n")
            
            # Check has_audio flag
            has_audio = audio.get('has_audio')
            print(f"   ⚠️ has_audio flag: {has_audio}")
            if not has_audio:
                print("   ❌ PROBLEM: has_audio is False or missing!")
                print("   This is why narrative service ignores audio!\n")
            else:
                print("   ✅ has_audio is True\n")
            
            # Check transcript
            if 'transcript' in audio:
                transcript = audio['transcript']
                segments = transcript.get('segments', [])
                print(f"   🗣️ Whisper transcript:")
                print(f"      Segments: {len(segments)}")
                if segments:
                    print(f"      First segment: {segments[0].get('text', '')[:50]}...\n")
            
            # Check audio events
            if 'audio_events' in audio:
                events = audio['audio_events']
                print(f"   ⚡ Audio events: {len(events)}")
                if events:
                    event_types = list(set([e.get('description', '') for e in events[:5]]))
                    print(f"      Types: {', '.join(event_types)}\n")
            
            # Check fused data
            if 'fused_data' in audio:
                fused = audio['fused_data']
                timeline = fused.get('timeline', [])
                confirmations = fused.get('audio_confirmations', 0)
                print(f"   🔗 Audio-visual fusion:")
                print(f"      Timeline moments: {len(timeline)}")
                print(f"      Visual confirmations: {confirmations}\n")
            
            # Show what narrative service needs
            print("📋 NARRATIVE SERVICE REQUIREMENTS:")
            print("   The narrative service checks:")
            print("   1. audio.get('has_audio') must be True ✓" if has_audio else "   1. audio.get('has_audio') must be True ✗")
            print("   2. transcript.get('segments') should have data")
            print("   3. audio_events list should exist")
            print("   4. fused_data.timeline should exist\n")
            
        else:
            print("❌ NO audio_analysis IN S3!")
            print("   The detections.json file doesn't contain audio_analysis\n")
        
        # Check detections
        detections = data.get('detections', [])
        print(f"📊 DETECTIONS: {len(detections)} total")
        if detections:
            first = detections[0]
            print(f"   First detection has model_source: {first.get('model_source', 'MISSING')}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    check_audio_in_s3()
