import speech_recognition as sr
from gtts import gTTS
import pyaudio
import numpy as np
import os
import time
import RPi.GPIO as GPIO
from collections import Counter
import wave
from datetime import datetime
import glob
import re

RATE = 96000
CHUNK = 256
r = sr.Recognizer()
MAX_INTENSITY_Array = [7500,7500,7500,7500]

SIGNAL_DICT = {
    (1, 1, 1, 1): 'Start signal',
    (1, 0, 0, 0): '1',
    (1, 1, 0, 0): '2',
    (1, 0, 1, 0): '3',
    (1, 0, 0, 1): '4',
    (1, 1, 0, 1): '5',
    (1, 0, 1, 1): '6',
    (0, 1, 0, 0): '7',
    (0, 1, 1, 0): '8',
    (0, 1, 0, 1): '9',
    (0, 1, 1, 1): '0',
    (0, 0, 1, 0): 'Dot',
    (0, 0, 1, 1): 'End signal',
}

wake_words = ["hey google", "ok google", "hi google","hello google","okay google"]

activate_words = [
    "blood sugar",
    "blood glucose",
    "blood sugar test",
    "blood glucose test",
]



BPM_activation_words = [
    "blood pressure meter test",
    "blood pressure meter",
    "start blood pressure meter",
    "activate blood pressure meter",
    "turn on blood pressure meter",
    "blood pressure monitor",
]

calibration_activation_words = [
    "calibration",
    "ultrasound calibration"
]

#set GPIO for LED light
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(17,GPIO.OUT)

#TTS command
def speak(text):
    tts = gTTS(text=text, lang='en')
    filename = 'voice.mp3'
    tts.save(filename)
    os.system('play ' + filename)

#audio analysis
def analyze_audio(audio_data, rate, target_frequencies, MAX_INTENSITY):
    fft = np.fft.fft(audio_data)
    freq = np.fft.fftfreq(len(fft), 1.0/rate)
    
    frequencies_detected = [0 for _ in target_frequencies]
    for i, target_freq in enumerate(target_frequencies):
        idx = np.argmin(np.abs(freq - target_freq))
        intensity = np.abs(fft[idx])
        if intensity > MAX_INTENSITY[i]:
            frequencies_detected[i] = 1
    return tuple(frequencies_detected)

def calibration_analyze_audio(audio_data, rate, target_frequencies):
    fft = np.fft.fft(audio_data)
    freq = np.fft.fftfreq(len(fft), 1.0/rate)
    intensity = []
    frequencies_detected = [0 for _ in target_frequencies]
    for i, target_freq in enumerate(target_frequencies):
        idx = np.argmin(np.abs(freq - target_freq))
        intensity.append(np.abs(fft[idx]))
    return intensity

def process_string(s):
    if len(s) >= 10:
        counter = Counter(s)
        most_common_char = counter.most_common(1)[0][0]
        print(s)
        return most_common_char
    return ""

#main
def run_ultrasound_test():
    try:
        print("Ultrasound testing")
        speak("Start blood glucose meter momitoring")
        # Start PyAudio stream
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
        try:
            # detected = False
            # is_recording = False
            # Data_start_time = 0
            # current_data = ""
            result = ""
            ultrasound_start = time.time()
            TARGET_FREQUENCIES = [18000, 20000, 21000, 22000]
            last_data = ""
            current_data = ""
            max_counter = 0
            while True:
                # Record audio
                try:
                    data = np.frombuffer(stream.read(CHUNK), dtype=np.int16)
                except IOError:
                    continue  # Ignore the error and continue
                # Analyze audio
                freqs_detected = analyze_audio(data, RATE,TARGET_FREQUENCIES, MAX_INTENSITY_Array)
                if((time.time() - ultrasound_start) > 40):
                    speak("timeout")
                    turn_off_led()
                    time.sleep(0.15)
                    turn_on_led()
                    time.sleep(0.15)
                    return
                
                if freqs_detected in SIGNAL_DICT:
                    if(not detected):
                        Data_start_time = time.time()
                    if(time.time() - Data_start_time > 0):
                        if(SIGNAL_DICT[freqs_detected] == 'Start signal'):
                            current_data += 'S'
                        elif(SIGNAL_DICT[freqs_detected] == 'End signal'):
                            current_data += 'E'
                        else:
                            if(SIGNAL_DICT[freqs_detected] == 'Dot'):
                                current_data += 'D'
                            else:
                                current_data += SIGNAL_DICT[freqs_detected]
                    detected = True
                else:
                    if(detected):
                        duration = time.time() - Data_start_time
                        if(duration > 0.1 and current_data):
                            processed_string = process_string(current_data)
                            if processed_string:
                                print(processed_string)
                                if(processed_string == 'S'):
                                    if(is_recording):
                                        result = ""
                                    is_recording = True
                                elif(processed_string == 'E'):
                                    if(is_recording):
                                        print("speak : " + result)
                                        speak_Text = "Your blood glucose level is " + result + " Mg/dL."
                                        speak(speak_Text)
                                        break
                                    result = ""
                                    is_recording = False
                                elif(is_recording):
                                    result+=processed_string
                            current_data = ""
                    detected = False
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
    except (IOError, OSError) as e:
        print(f"File error occurred: {e}")

def run_BPM_ultrasound_test():
    try:
        print("BPM Ultrasound testing")
        speak("Start blood pressure momitor testing")
        # Start PyAudio stream
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
        try:
            detected = False
            is_recording = False
            Data_start_time = 0
            current_data = ""
            result = ""
            ultrasound_start = time.time()
            ultrasound_timeout = time.time()
            TARGET_FREQUENCIES = [18000, 20000, 21000, 22000]
            while True:
                # Record audio
                try:
                    data = np.frombuffer(stream.read(CHUNK), dtype=np.int16)
                except IOError:
                    continue  # Ignore the error and continue
                # Analyze audio
                freqs_detected = analyze_audio(data, RATE,TARGET_FREQUENCIES, MAX_INTENSITY_Array)
                if((time.time() - ultrasound_start) > 150):
                    speak("timeout")
                    turn_off_led()
                    time.sleep(0.15)
                    turn_on_led()
                    time.sleep(0.15)
                    return
                if freqs_detected in SIGNAL_DICT:
                    ultrasound_timeout = time.time()
                    if(not detected):
                        Data_start_time = time.time()
                    if(time.time() - Data_start_time > 0):
                        if(SIGNAL_DICT[freqs_detected] == 'Start signal'):
                            current_data += 'S'
                        elif(SIGNAL_DICT[freqs_detected] == 'End signal'):
                            current_data += 'E'
                        else:
                            if(SIGNAL_DICT[freqs_detected] == 'Dot'):
                                current_data += 'D'
                            else:
                                current_data += SIGNAL_DICT[freqs_detected]
                    detected = True
                else:
                    if(detected):
                        duration = time.time() - Data_start_time
                        if(duration > 0.1 and current_data):
                            processed_string = process_string(current_data)
                            if processed_string:
                                print(processed_string)
                                if(processed_string == 'S'):
                                    if(is_recording):
                                        result = ""
                                    is_recording = True
                                elif(processed_string == 'E'):
                                    if(is_recording):
                                        print("speak : " + result)
                                        numbers = re.findall(r'\d+', result)
                                        if len(numbers) < 3:
                                            print("error : decoding error")
                                            speak("error : decoding error")
                                        else:
                                            print(numbers) 
                                            print("SYS:", numbers[0])
                                            print("DIA:", numbers[1])
                                            print("Pulse:", numbers[2])
                                            speak_Text = "Your blood pressure test results are as follows: systolic pressure is " + str(numbers[0]) + ", diastolic pressure is " + str(numbers[1]) + ", and heart rate is " + str(numbers[2]) + "."
                                            speak(speak_Text)
                                        break
                                    result = ""
                                    is_recording = False
                                elif(is_recording):
                                    result+=processed_string
                            current_data = ""
                        if(ultrasound_timeout - time.time() > 2.5):
                            current_data = ""
                    detected = False
        finally:
            # Stop PyAudio stream
            stream.stop_stream()
            stream.close()
            p.terminate()
    except (IOError, OSError) as e:
        print(f"File error occurred: {e}")

def run_ultrasound_calibration():
    try:
        print("ultrasound calibration testing")
        speak("Start ultrasound calibration testing")
        # Start PyAudio stream
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
        try:
            TARGET_FREQUENCIES = [18000, 20000, 21000, 22000]
            RECORD_SECONDS = 5
            ultrasound_data = []
            analyze_result = []
            ultrasound_start_time = time.time()
            average_test = [[], [], [], []]
            average_result = []
            while True:
                # Record audio
                try:
                    data = np.frombuffer(stream.read(CHUNK), dtype=np.int16)
                except IOError:
                    continue  # Ignore the error and continue
                # Analyze audio
                if((time.time() - ultrasound_start_time) < RECORD_SECONDS):
                    ultrasound_data.append(data[:])
                else:
                    for data in ultrasound_data:
                        analyze_result.append(calibration_analyze_audio(data, RATE, TARGET_FREQUENCIES))
                    test = len(analyze_result)
                    for data in analyze_result:
                        average_test[0].append(data[0])
                        average_test[1].append(data[1])
                        average_test[2].append(data[2])
                        average_test[3].append(data[3])

                    average_result = [((sum(data) / test)*0.7) for data in average_test]
                    global MAX_INTENSITY_Array
                    MAX_INTENSITY_Array = average_result
                    print(MAX_INTENSITY_Array)
                    speak_Text = "result : " + str(MAX_INTENSITY_Array[0]) + str(MAX_INTENSITY_Array[1]) + str(MAX_INTENSITY_Array[2]) + str(MAX_INTENSITY_Array[3])
                    speak(speak_Text)
                    break
                # freqs_detected = analyze_audio(data, RATE,TARGET_FREQUENCIES, MAX_INTENSITY_Array)
        finally:
            # Stop PyAudio stream
            stream.stop_stream()
            stream.close()
            p.terminate()
    except (IOError, OSError) as e:
        print(f"File error occurred: {e}")

#RaspberryPi GPIO
def turn_on_led():
    GPIO.output(17,GPIO.HIGH)
    return
def turn_off_led():
    GPIO.output(17,GPIO.LOW)
    return

is_wake = False

#STT command
def get_command():
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    output_folder = "output"
    os.makedirs(output_folder, exist_ok=True)
    output_file_path = os.path.join(output_folder, f"{current_time}.wav")

    with sr.Microphone() as source:
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            with wave.open(output_file_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(audio.sample_width)
                wav_file.setframerate(audio.sample_rate)
                wav_file.writeframes(audio.get_wav_data())
            # 檢查資料夾中的WAV檔案數量
            wav_files = glob.glob(os.path.join(output_folder, '*.wav'))
            if len(wav_files) > 20:
                oldest_file = min(wav_files, key=os.path.getctime)
                os.remove(oldest_file)
            return r.recognize_google(audio)
        except sr.WaitTimeoutError:
            print("Timeout error: No speech detected within the timeout limit. Trying again...")
        except sr.UnknownValueError:
            print("Sorry, command was not understood. Trying again...")
            if(is_wake):
                speak("sorry i couldn't understand what you meant.")
                turn_off_led()
                time.sleep(0.15)
                turn_on_led()
                time.sleep(0.15)
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}. Waiting 10 seconds before trying again.")
        return None

speak("I am ready")

#main loop
while True:
    print("Waiting for wake word command...")
    is_wake = False
    turn_off_led()
    text = get_command()
    if text is None:
        continue
    print(f"You said: {text}")
    # 如果識別到喚醒詞
    if any(wake_word in text.lower() for wake_word in wake_words):
        turn_on_led()
        speak("I am here.")
        is_wake = True
        print("Google Assistant activated. Waiting for activation command...")
        command = get_command()
        if command is None:
            continue
        print(f"You said: {command}")
        # 如果識別到啟動詞
        if any(activate_word in command.lower() for activate_word in activate_words):
            run_ultrasound_test()
        # 如果識別到啟動詞
        elif any(activate_word in command.lower() for activate_word in home_security_activation_words):
            run_home_security()
        elif any(activate_word in command.lower() for activate_word in BPM_activation_words):
            run_BPM_ultrasound_test()
        elif any(activate_word in command.lower() for activate_word in calibration_activation_words):
            run_ultrasound_calibration()
        else:
            turn_off_led()
            time.sleep(0.15)
            turn_on_led()
            time.sleep(0.15)

