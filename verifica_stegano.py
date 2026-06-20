import cv2
import numpy as np
import glob

def decodare_steganografie(nume_imagine):
    print(f"Analizam fisierul: {nume_imagine} ...")

    imagine = cv2.imread(nume_imagine)

    if imagine is None:
        print("   EROARE: Nu am putut citi imaginea! Verifica daca exista.")
        return

    imagine_1d = imagine.flatten() #transforma imaginea într-un vector 1D lung

    pas = 10
    pixeli_modificati = imagine_1d[::pas]

    biti_lsb = pixeli_modificati & 1 #extragem doar ultimul bit (LSB) din pixelii selectati

    biti_string = ''.join(biti_lsb.astype(str)) #transformam array-ul de biti într-un string lung

    mesaj_decodat = ""
    marcaj_gasit = False

    for i in range(0, len(biti_string), 8):
        octet = biti_string[i:i + 8]

        if len(octet) < 8:
            break

        if octet == '00000000':
            marcaj_gasit = True
            break

        mesaj_decodat += chr(int(octet, 2)) #convertim pachetul de 8 biti în litera/cifra

    if marcaj_gasit and mesaj_decodat:
        print("   SUCCES! Am extras codul de securitate:")
        print(f"   >> {mesaj_decodat} <<\n")
    else:
        print("    EROARE: Nu a fost gasit niciun cod secret (sau imaginea e compromisa).\n")

if __name__ == "__main__":
    print("\n INITIERE SCANARE AUTOMATA STEGANOGRAFIE \n")

    lista_poze_martor = glob.glob("folder_stegano/dovada_*.png")

    if len(lista_poze_martor) == 0:
        print("Nu am gasit nicio poza martor (dovada_*.png) in folderul curent.")
    else:
        print(f"Am gasit {len(lista_poze_martor)} poze martor. Incepem decodarea...\n")

        for fisier in lista_poze_martor:
            decodare_steganografie(fisier)

    print(" SCANARE FINALIZATA.")