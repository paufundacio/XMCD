# -*- coding: utf-8 -*-

################# IMPORTS #################

# Selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Utilitats
from datetime import datetime
from time import sleep
from os import remove

# Mòduls
from selenium_helpers import cerca_dades, cerca_cerca
from postgres import connecta_bd, guarda, registra_error
from utils import nom_sensor

# Globals
import logging
import sys
import argparse


import json
with open('config.json', 'r') as file:
    globals = json.load(file)

### GLOBALS ###

directori_Imatges = globals['directori_Imatges']
temps_espera_processos = globals['temps_espera_processos']
temps_espera_cerques = globals['temps_espera_cerques']
fitxer_logs = globals['fitxer_logs']

# Fitxer de logs
logging.basicConfig(filename=fitxer_logs, level=logging.DEBUG)

### ARGUMENTS ###
parser = argparse.ArgumentParser(description='Rep quin navegador i cercador utilitzarà per paràmetre')
parser.add_argument('navegador', type=str, help='Quin navegador? Chrome / Firefox')
parser.add_argument('cercador',  type=str, help='Quin cercador? Google / Bing')
args = parser.parse_args()

### BASE DE DADES ###

if not connecta_bd():
    logging.error(f"El dispositiu no té connexió a internet")
    sys.exit(503)
else:
    conn, cursor = connecta_bd()

### SENSOR ###

# Cerca el nom de la màquina
if nom_sensor() is not None:
    sensor = nom_sensor()
else:
    logging.error(f"No s'ha agafat el nom de sensor")
    sys.exit(1)

### FUNCIONS ###

# Navegador
if args.navegador == 'Chrome':
    # Fem l'import de les funcions de Chrome
    from chromeUtils import inicia_navegador
elif args.navegador == 'Firefox':
    from firefoxUtils import inicia_navegador
else:
    logging.error(f"El navegador {args.navegador} no està acceptat")
    sys.exit(2)

# Cercador
if args.cercador == 'Google':
    # Fem l'import de les funcions de Chrome
    from googleUtils import inicia_cercador
else:
    logging.error(f"El navegador {args.navegador} no està acceptat")
    sys.exit(2)

### NAVEGADOR ###

# Iniciem el navegador
navegador, browser = inicia_navegador(cursor)

# Control errors del navegador
if browser == 3:
    logging.error(f"No s'ha pogut agafar correctament el User Agent amb {args.navegador}")
    sys.exit(3)
elif browser == 10:
    logging.error(f"No s'ha pogut iniciar correctament el driver del navegador {args.navegador}")
    sys.exit(10)

### CERCA ###

# Obté la cadena a buscar al cercador
int_cerca, cerca = cerca_cerca(conn, cursor, sensor)

# Definim el diccionari on es guardaran les dades
resultats = {}

### CERCADOR ###

# Iniciem el cercador
cercador = inicia_cercador(browser, cerca)

# Control errors del cercador
if browser == 20:
    logging.error(f"No s'ha pogut iniciar correctament el cercador {args.cercador}")
    sys.exit(20)
elif browser == 21:
    logging.error(f"No s'han pogut acceptar les cookies del cercador {args.cercador}")
    sys.exit(21)
elif browser == 22:
    logging.error(f"No s'ha pogut realitzar la cerca {cerca} del cercador {args.cercador}")
    sys.exit(22)

# Calen fer temps d'espera per a que es carreguin els elements
sleep(temps_espera_cerques)

# Obté els resultats
logging.info(f"Cercant els resultats de {cerca}...")

# Nº de resultats guardats
resultats_desats = 1

# Cal desar 10 resultats sempre
while resultats_desats <= 10:

    # Defineix les variables de les imatges
    nom_captura_1 = directori_Imatges + sensor + cerca.replace(' ', '_') + str(datetime.now()).replace(' ', '_')+'.png'
    nom_captura_2 = directori_Imatges + sensor + cerca.replace(' ', '_') + str(datetime.now()).replace(' ', '_')+'_2a.png'

    # Guarda la captura de la pantalla principal
    browser.save_screenshot(nom_captura_1)

    # A Google els resultats son tots els títols <h3>
    # Busquem tots els elements <a> que contenen un <h3>
    resultats_cerca = browser.find_elements(By.XPATH, '//a[h3]')

    # Agafem els resultats
    for resultat in resultats_cerca:

        # Mentre hi hagin menys de 10
        if resultats_desats < 11:

            link, titol, description = cerca_dades(resultat)

            # Si una de les respostes és un més resultats, se'n va a la 2a pàgina de Google
            if titol == "Més resultats":

                logging.info(f"Obtenint la segona pàgina de {cerca}...")

                browser.get(link)

                sleep(temps_espera_processos)

                # Guarda la captura de la segona pantalla
                browser.save_screenshot(nom_captura_2)

                # Busca a la segona pàgina de Google
                a_elements_with_h3 = browser.find_elements(By.XPATH, '//a[h3]')
                for a in a_elements_with_h3:
                    if resultats_desats < 11:
                        
                        ############### Això podria ser la funció cerca dades que crida a la (guarda_resultat). Valorar

                        link, titol, description = cerca_dades(a)

                        if link is not None:
                            resultats[resultats_desats] = {'titol': titol, 'url': link, 'description': description}
                            resultats_desats += 1

                    # Un cop tenim 10 resultats.
                    else:
                        logging.info(f"S'han agafat els 10 resultats a la segona pàgina de {cerca}...")
                        browser.execute_script("window.history.go(-1)")
                        sleep(temps_espera_processos)
                        break

            # Guarda la pàgina. No és un enllaç de més resultats.
            else:
                ############### Això podria ser una funció individual (guarda_resultat)
                if link is not None:
                    resultats[resultats_desats] = {'titol': titol, 'url': link, 'description': description}
                    resultats_desats += 1

    # Si no hi han 10 respostes cerca el botó de següent pàgina
    if resultats_desats < 11:
        # Si no troba el botó de la segona pàgina peta. 
        try:
            # Prem al botó de la segona pàgina
            browser.find_elements(By.XPATH, '//a[@aria-label=\'Page 2\']')[0].click()

            # Esperem a que carreguin els elements
            sleep(temps_espera_processos)

            # Guarda la captura de la segona pantalla
            browser.save_screenshot(nom_captura_2)

            # Busquem tots els elements <a> que contenen un <h3>
            a_elements_with_h3 = browser.find_elements(By.XPATH, '//a[h3]')

            for a in a_elements_with_h3:
                # Mentre hi hagin menys de 10
                if resultats_desats < 11:
                    # Cerca les dades
                    link, titol, description = cerca_dades(a)

                    if link is not None:
                        resultats[resultats_desats] = {'titol': titol, 'url': link, 'description': description}
                        resultats_desats += 1
                else:
                    browser.execute_script("window.history.go(-1)")
                    sleep(temps_espera_processos)
                    break
        except:
            # Si peta no podem fer res. Esperar i tornar a reiniciar la cerca.
            sleep(temps_espera_cerques)
            logging.error(f"No s'ha pogut fer la petició de la segona pàgina de {cerca}")

    logging.info(f"Valorant els resultats de {cerca}...")

    # Si al final de tot no ha trobat 10 resultats torna a fer la cerca:
    if resultats_desats < 11:

        logging.info(f"No s'han obtingut els 10 resultats de {cerca}...")

        # Esborra les captures
        remove(nom_captura_1)
        try:
            remove(nom_captura_2)

        except:
            pass

        finally:

            # Torna a definir els paràmetres de la cerca actual
            logging.debug(f"Esborrades les captures de pantalla")
            resultats_desats = 1
            resultats[cerca] = {}
            browser.get('https://google.com')
            sleep(temps_espera_cerques)
            textarea = browser.find_element(By.TAG_NAME, value='textarea')    
            textarea.send_keys(cerca + Keys.ENTER)
            sleep(temps_espera_processos)
            logging.info(f"Torna a realitzar la cerca")


    #Desa les dades
    else:
        logging.info(f"Guardant a la base de dades")
        for posicio, dades in resultats.items():
            titol = dades['titol']
            url = dades['url']
            descripcio = dades['description']
            llengua = "--"

            guarda(conn, cursor, sensor, navegador, cercador, int_cerca, posicio, titol, url, descripcio, llengua)

conn.close()

browser.quit()

logging.info(f"Crawler finalitzat correctament")
sys.exit(0)
