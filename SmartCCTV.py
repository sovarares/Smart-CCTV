import cv2
import numpy as np
import time
import datetime
import threading
import sounddevice as sd
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from scipy.io.wavfile import write
import moviepy.editor as mpe
from flask import Flask, Response
import atexit
import signal

app = Flask(__name__)  # aplicatia web

# configurare email
EMAIL_SENDER = "xtremecookie209@gmail.com"
EMAIL_PASSWORD = "yxuj xjdt yztt gmoz"
EMAIL_RECEIVER = "ioan_rares.sova@stud.acs.upb.ro"

# variabile globale si configurare foldere
cadru_curent = None
se_inregistreaza = False
TIMP_DE_GRATIE = 5.0
oprire_solicitata = False

FOLDER_STEGANO = "folder_stegano"
FOLDER_VIDEO = "folder_video"

os.makedirs(FOLDER_STEGANO, exist_ok=True)
os.makedirs(FOLDER_VIDEO, exist_ok=True)

# lista globala pentru a tine evidenta multiplexarilor in curs
threaduri_mux_active = []


def asteapta_salvarile_la_iesire():
    threaduri_in_lucru = [t for t in threaduri_mux_active if t.is_alive()]
    if threaduri_in_lucru:
        print(f"\n[ATENTIE] Asteptam finalizarea a {len(threaduri_in_lucru)} procesari video (multiplexare)...")
        for t in threaduri_in_lucru:
            t.join()
        print("[SUCCES] Toate salvarile video s-au incheiat! Programul se inchide in siguranta.")


atexit.register(asteapta_salvarile_la_iesire)  # inregistreaza functia de mai sus în sistemul de iesire Python


def trimite_email_alerta(cale_imagine):
    try:
        msg = MIMEMultipart()  # Creeaza containerul de email
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = "ALERTA MISCARE!"

        msg.attach(MIMEText("Alerta!", 'plain'))

        with open(cale_imagine, 'rb') as f:
            img_data = f.read()
        image = MIMEImage(img_data, name=os.path.basename(cale_imagine))  # pregăteste imaginea ca atasament
        msg.attach(image)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # securizeaza conexiunea
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"[{time.strftime('%H:%M:%S')}] Email cu alerta trimis cu succes!")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Eroare la trimiterea emailului: {e}")


def obtine_urmatorul_numar_alerta():
    fisiere = os.listdir(FOLDER_VIDEO)  # lista cu toate fisierele din folder
    numere = []
    for f in fisiere:
        match = re.match(r'alerta(\d+)', f)  # cauta tiparul "alerta" urmat de cifre
        if match:
            numere.append(int(match.group(1)))  # extrage doar numarul gasit

    if not numere:
        return 1
    return max(numere) + 1


def aplica_steganografie_lsb(imagine, text_secret):
    # transforma textul in binar si adauga 8 zerouri ca semn de stop la citire
    text_binar = ''.join(format(ord(char), '08b') for char in text_secret) + '00000000'
    lungime_bits = len(text_binar)

    imagine_stegano = imagine.copy()
    imagine_1d = imagine_stegano.flatten()

    pas = 10  # ascundem un bit la fiecare 10 pixeli
    if lungime_bits * pas > len(imagine_1d):
        return imagine  # daca mesajul e prea mare pentru imagine, nu facem nimic

    # selectam pixelii de modificat folosind slicing [start:stop:pas]
    pixeli_vizati = imagine_1d[:lungime_bits * pas: pas].astype(np.uint16)
    biti_text_array = np.array(list(text_binar), dtype=np.uint16)  # convertim sirul de 0 si 1 în numere

    pixeli_modificati = (pixeli_vizati & 254) | biti_text_array  # face 0 ultimul bit, apoi | biti_text_array pune bitul nostru
    imagine_1d[:lungime_bits * pas: pas] = pixeli_modificati.astype(np.uint8)  # punem pixelii modificati inapoi

    imagine_stegano = imagine_1d.reshape(imagine.shape)
    return imagine_stegano


def inregistreaza_audio_dinamic(cale_fisier_audio, semnal_start_audio=None):
    fs = 44100  # frecventa de esantionare
    cadre_audio = []

    def callback_audio(indata, frames, timp, status):
        if se_inregistreaza:
            cadre_audio.append(indata.copy())  # adauga sunetul în lista daca suntem în alerta

    # porneste fluxul de intrare audio
    stream = sd.InputStream(samplerate=fs, channels=2, dtype='float32', callback=callback_audio)

    with stream:
        if semnal_start_audio:
            semnal_start_audio.set()
        while se_inregistreaza:
            time.sleep(0.01)  # asteapta cat timp inregistrarea video este activa

    if len(cadre_audio) > 0:
        inregistrare_completa = np.concatenate(cadre_audio, axis=0)  # uneste toate bucătile de sunet
        inregistrare_amplificata = np.clip(inregistrare_completa * 20.0, -1.0, 1.0)
        write(cale_fisier_audio, fs, inregistrare_amplificata)


def proceseaza_alerta(nume_baza, thread_audio_de_asteptat):
    thread_audio_de_asteptat.join()  # asteapta ca inregistrarea audio să fie salvata pe disc
    time.sleep(0.5)  # mica pauza pentru a asigura scrierea fisierului

    fisier_video = os.path.join(FOLDER_VIDEO, f"{nume_baza}.avi")
    fisier_audio = os.path.join(FOLDER_VIDEO, f"{nume_baza}.wav")
    fisier_final = os.path.join(FOLDER_VIDEO, f"{nume_baza}_COMPLET.mp4")
    fisier_temp_audio = os.path.join(FOLDER_VIDEO, f"{nume_baza}_TEMP_audio.m4a")

    print(f"[{time.strftime('%H:%M:%S')}] Incepem MULTIPLEXAREA pentru {nume_baza}_COMPLET.mp4...")
    try:
        clip_video = mpe.VideoFileClip(fisier_video)
        clip_audio = mpe.AudioFileClip(fisier_audio)

        # luam durata cea mai mica pentru a ne asigura ca se termina exact in acelasi timp
        durata_minima = min(clip_video.duration, clip_audio.duration)

        # taiem ambele clipuri la exact aceeasi durata
        clip_video = clip_video.subclip(0, durata_minima)
        clip_audio = clip_audio.subclip(0, durata_minima)

        clip_final_export = clip_video.set_audio(clip_audio)

        # exporta rezultatul final ca MP4
        clip_final_export.write_videofile(
            fisier_final,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=fisier_temp_audio,
            remove_temp=True,
            verbose=False,
            logger=None
        )

        clip_video.close()
        clip_audio.close()
        print(f"[{time.strftime('%H:%M:%S')}] SUCCES: Fisierul a fost salvat in -> {fisier_final}")
    except Exception as e:
        print(f"Eroare la multiplexare: {e}")

    fisiere_gunoi = [fisier_video, fisier_audio, fisier_temp_audio]
    for fisier in fisiere_gunoi:
        incercari = 0
        while incercari < 5:
            try:
                if os.path.exists(fisier):
                    os.remove(fisier)
                break
            except OSError:
                time.sleep(1.0)
                incercari += 1


def camera_cctv_loop():
    global cadru_curent, se_inregistreaza, threaduri_mux_active, oprire_solicitata

    cap = cv2.VideoCapture(0)  # deschide accesul la camera web
    fourcc = cv2.VideoWriter.fourcc(*'XVID')

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()  # citeste al doilea cadru pentru comparatie

    out = None
    timp_ultima_miscare = 0
    nume_baza_curent = ""
    thread_audio_curent = None
    email_trimis_alerta_curenta = False

    print("CCTV PORNIT. Monitorizare activa...")

    while True:
        if oprire_solicitata:
            if se_inregistreaza:
                print(f"\n[{time.strftime('%H:%M:%S')}] Oprire solicitata! Finalizam si procesam inregistrarea...")
                se_inregistreaza = False
                if out is not None:
                    out.release()

                # unire audio-video
                thread_mux = threading.Thread(target=proceseaza_alerta, args=(nume_baza_curent, thread_audio_curent))
                thread_mux.daemon = False
                threaduri_mux_active.append(thread_mux)
                thread_mux.start()

            cap.release()  # eliberam camera web
            break

        if frame1 is None or frame2 is None:
            time.sleep(1)
            ret, frame1 = cap.read()
            ret, frame2 = cap.read()
            continue

        # algoritmul de detectie a miscarii
        diff = cv2.absdiff(frame1, frame2)  # calculeaza diferenta absoluta între doua cadre consecutive
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)  # transforma diferenta în alb-negru
        blur = cv2.GaussianBlur(gray, (11, 11), 0)  # aplica blur pentru a ignora zgomotul
        _, thresh = cv2.threshold(blur, 20, 255,
                                  cv2.THRESH_BINARY)  # face imaginea alb-negru pur, 20 fiind pragul, >20 => devine alb, altfel devine negru
        dilated = cv2.dilate(thresh, None, iterations=3)  # largeste zonele albe pentru a uni contururile
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE,
                                       cv2.CHAIN_APPROX_SIMPLE)  # gaseste marginile formelor detectate

        miscare_acum = False
        for contour in contours:
            if cv2.contourArea(contour) < 800:
                continue  # ignora obiectele foarte mici
            miscare_acum = True
            (x, y, w, h) = cv2.boundingRect(contour)  # calculeaza dreptunghiul în jurul miscării
            cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 255, 0), 2)  # deseneaza dreptunghiul

        if miscare_acum:
            timp_ultima_miscare = time.time()
            if not se_inregistreaza:
                se_inregistreaza = True
                email_trimis_alerta_curenta = False

                nr = obtine_urmatorul_numar_alerta()
                nume_baza_curent = f"alerta{nr}"

                print(f"[{time.strftime('%H:%M:%S')}] ALERTA NOUA: {nume_baza_curent}. Initializam inregistrarea...")

                cale_video = os.path.join(FOLDER_VIDEO, f"{nume_baza_curent}.avi")
                cale_audio = os.path.join(FOLDER_VIDEO, f"{nume_baza_curent}.wav")

                semnal_audio_gata = threading.Event()  # cream semnalul

                # pornim inregistrarea audio si ii pasam semnalul de sincronizare
                thread_audio_curent = threading.Thread(target=inregistreaza_audio_dinamic,
                                                       args=(cale_audio, semnal_audio_gata))
                thread_audio_curent.start()

                out = cv2.VideoWriter(cale_video, fourcc, 30.0, (frame1.shape[1], frame1.shape[0]))

                #asteptam ca firul de executie audio sa trimita semnalul ca e gata
                semnal_audio_gata.wait()

                #pornim cronometrul
                timp_start_inreg = time.time()
                cadre_scrise = 0

        if se_inregistreaza:
            cv2.putText(frame1, "REC", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            if out is not None:
                # calculam cate cadre ar fi trebuit sa avem pana in acest moment
                timp_trecut = time.time() - timp_start_inreg
                cadre_asteptate = int(timp_trecut * 30.0)

                #aplicam steganografia doar la primul cadru si apoi o data pe secunda
                if cadre_scrise % 30 == 0:
                    cod_secret = f"SECURED_{nume_baza_curent}_{datetime.datetime.now().strftime('%H%M%S')}"
                    cadru_de_scris = aplica_steganografie_lsb(frame1, cod_secret)
                else:
                    cadru_de_scris = frame1

                # scriem variabila corecta si optimizata
                while cadre_scrise < cadre_asteptate:
                    out.write(cadru_de_scris)
                    cadre_scrise += 1

            if not email_trimis_alerta_curenta:
                # salvam prima imagine ca dovada PNG (folosim cadru_de_scris care stim sigur ca e securizat)
                cale_imagine_martor = os.path.join(FOLDER_STEGANO, f"dovada_{nume_baza_curent}.png")
                cv2.imwrite(cale_imagine_martor, cadru_de_scris)

                # trimitem emailul pe un thread separat ca sa nu oprim camera
                threading.Thread(target=trimite_email_alerta, args=(cale_imagine_martor,), daemon=True).start()
                email_trimis_alerta_curenta = True

            if time.time() - timp_ultima_miscare >= TIMP_DE_GRATIE:
                print(f"[{time.strftime('%H:%M:%S')}] Miscare oprita. Finalizam clipul...")
                se_inregistreaza = False
                if out is not None:
                    out.release()

                threaduri_mux_active = [t for t in threaduri_mux_active if t.is_alive()]

                # unire audio-video
                thread_mux = threading.Thread(target=proceseaza_alerta, args=(nume_baza_curent, thread_audio_curent))
                thread_mux.daemon = False
                threaduri_mux_active.append(thread_mux)
                thread_mux.start()

        cadru_curent = frame1.copy()
        frame1 = frame2
        ret, frame2 = cap.read()


def genereaza_stream_web():
    global cadru_curent
    while True:
        if cadru_curent is not None:
            cadru_mic = cv2.resize(cadru_curent, (640, 480))
            ret, buffer = cv2.imencode('.jpg', cadru_mic, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            cadru_comprimat = buffer.tobytes()
            # codul standard pentru stream video MJPEG în HTTP
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + cadru_comprimat + b'\r\n')
            time.sleep(0.03)  # trimitem aproximativ 30 de cadre pe secunda
        else:
            time.sleep(0.1)


@app.route('/oprire', methods=['POST'])
def opreste_serverul():
    global oprire_solicitata
    oprire_solicitata = True

    def trimite_semnal_oprire():
        time.sleep(1)  # asteptam o secunda ca camera să elibereze resursele

        # așteptam ca toate procesele video să fie gata inainte să dăm semnalul de Kill
        for t in threaduri_mux_active:
            if t.is_alive():
                t.join()

                # abia acum oprim fortat serverul
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=trimite_semnal_oprire).start()  # porneste thread-ul de inchidere

    return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sistem Oprit</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    background-color: #111;
                    color: #fff;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .container {
                    text-align: center;
                    background-color: #222;
                    padding: 40px;
                    border-radius: 12px;
                    border: 2px solid #ff4444;
                    box-shadow: 0 0 25px rgba(255, 68, 68, 0.3);
                    max-width: 500px;
                    width: 90%;
                }
                .icon {
                    font-size: 50px;
                    margin-bottom: 15px;
                }
                h1 {
                    color: #ff4444;
                    margin: 0 0 15px 0;
                    letter-spacing: 2px;
                }
                p {
                    color: #bbb;
                    font-size: 16px;
                    line-height: 1.6;
                    margin-bottom: 0; 
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">⚠️</div>
                <h1>SISTEM OPRIT</h1>
                <p>Camera a fost deconectata în siguranta.<br><br>Procesare media in curs. Va rugam sa nu inchideti fereastra terminalului pana la confirmarea salvarii complete a fisierelor în consola.</p>
            </div>
        </body>
        </html>
    '''


@app.route('/')
def index():
    return '''
        <html>
            <body style="background-color: #111; color: #0f0; text-align: center; font-family: monospace; margin: 0; padding-top: 20px;">
                <h1><< SMART CCTV LIVE STREAM >></h1>
                <img src="/video_feed" style="border: 2px solid #0f0; width: 100%; max-width: 850px; border-radius: 10px;">
                <br><br>
                <form action="/oprire" method="POST" style="display:inline;">
                    <button type="submit" style="background-color: red; color: white; padding: 15px 30px; border: none; font-size: 20px; font-weight: bold; border-radius: 5px; cursor: pointer;">OPRESTE CAMERA</button>
                </form>
            </body>
        </html>
    '''


@app.route('/video_feed')
def video_feed():
    return Response(genereaza_stream_web(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    thread_cctv = threading.Thread(target=camera_cctv_loop)
    thread_cctv.daemon = True
    thread_cctv.start()

    print("Accesati http://127.0.0.1:5000 in browser pentru a vedea camera live.")
    app.run(host='0.0.0.0', port=5000, threaded=True)