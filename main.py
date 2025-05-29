import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import tkinter as tk # Do pobrania wymiarów ekranu

KAHOOT_URL = "https://kahoot.it/"
active_drivers = []
lock = threading.Lock()

# --- Konfiguracja geometrii okien ---
SCREEN_WIDTH = 0
SCREEN_HEIGHT = 0
WINDOWS_PER_ROW_X = 5  # Ile okien w jednym rzędzie (oś X)
WINDOW_HEIGHT_Y = 300  # Stała wysokość okna
WINDOW_WIDTH_X = 0     # Obliczana szerokość okna
GAP_X = 0              # Odstęp między oknami w poziomie
GAP_Y = 0              # Odstęp między oknami w pionie (jeśli będzie więcej niż 1 rząd)

def setup_screen_geometry():
    global SCREEN_WIDTH, SCREEN_HEIGHT, WINDOW_WIDTH_X
    try:
        root = tk.Tk()
        root.withdraw() # Nie chcemy widzieć głównego okna tkinter
        SCREEN_WIDTH = root.winfo_screenwidth()
        SCREEN_HEIGHT = root.winfo_screenheight()
        root.destroy()

        # Oblicz szerokość pojedynczego okna, uwzględniając odstępy
        total_gap_width = (WINDOWS_PER_ROW_X - 1) * GAP_X
        available_width_for_windows = SCREEN_WIDTH - total_gap_width
        WINDOW_WIDTH_X = available_width_for_windows // WINDOWS_PER_ROW_X # Użyj // dla liczby całkowitej

        if WINDOW_WIDTH_X <= 0:
            print("BŁĄD: Obliczona szerokość okna jest nieprawidłowa. Sprawdź WINDOWS_PER_ROW_X i GAP_X.")
            WINDOW_WIDTH_X = 200 # Domyślna wartość awaryjna

        print(f"Ekran: {SCREEN_WIDTH}x{SCREEN_HEIGHT}, Okno: {WINDOW_WIDTH_X}x{WINDOW_HEIGHT_Y}, Okien/rząd: {WINDOWS_PER_ROW_X}")

    except Exception as e:
        print(f"BŁĄD: Nie udało się pobrać wymiarów ekranu lub obliczyć geometrii: {e}")
        # Ustaw domyślne wartości w razie problemu
        SCREEN_WIDTH = 1920
        SCREEN_HEIGHT = 1080
        WINDOW_WIDTH_X = (SCREEN_WIDTH - (WINDOWS_PER_ROW_X - 1) * GAP_X) // WINDOWS_PER_ROW_X
        if WINDOW_WIDTH_X <= 0: WINDOW_WIDTH_X = 200


def open_kahoot_in_thread(instance_number_zero_indexed): # Numer instancji zaczynający się od 0
    instance_display_number = instance_number_zero_indexed + 1 # Dla logów (1, 2, 3...)
    chrome_options = Options()
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # chrome_options.add_argument("--window-size={},{}".format(WINDOW_WIDTH_X, WINDOW_HEIGHT_Y)) # Można też tak, ale set_window_size jest bardziej elastyczne

    driver = None
    unique_nickname = f"sledzewski {instance_display_number}"
    game_pin = "214344"

    try:
        driver = webdriver.Chrome(options=chrome_options)
        with lock:
            active_drivers.append(driver)

        # --- Ustawianie rozmiaru i pozycji okna ---
        # Obliczanie pozycji dla bieżącego okna
        current_col = instance_number_zero_indexed % WINDOWS_PER_ROW_X
        current_row = instance_number_zero_indexed // WINDOWS_PER_ROW_X

        pos_x = current_col * (WINDOW_WIDTH_X + GAP_X)
        pos_y = current_row * (WINDOW_HEIGHT_Y + GAP_Y)

        # Sprawdzenie, czy okno zmieści się na ekranie (szczególnie w osi Y)
        if pos_y + WINDOW_HEIGHT_Y > SCREEN_HEIGHT:
            print(f"[Instancja {instance_display_number}] OSTRZEŻENIE: Okno może nie zmieścić się w pionie. Pozycja Y: {pos_y}")
            # Można by tu zresetować pos_y lub zaimplementować przewijanie, ale na razie tylko ostrzeżenie

        driver.set_window_size(WINDOW_WIDTH_X, WINDOW_HEIGHT_Y)
        driver.set_window_position(pos_x, pos_y)
        print(f"[Instancja {instance_display_number}] Rozmiar: {WINDOW_WIDTH_X}x{WINDOW_HEIGHT_Y}, Pozycja: {pos_x},{pos_y}")


        driver.get(KAHOOT_URL)
        wait = WebDriverWait(driver, 200)
        time.sleep(1)
        try:
            pin_input_locator = (By.ID, "game-input")
            pin_input_field = wait.until(EC.element_to_be_clickable(pin_input_locator))
            pin_input_field.send_keys(game_pin)
            # print(f"[Instancja {instance_display_number}] PIN '{game_pin}' wpisany.") # Mniej printów
        except TimeoutException:
            print(f"[Instancja {instance_display_number}] BŁĄD: Pole PIN nie znalezione (timeout).")
            return
        except Exception as e:
            print(f"[Instancja {instance_display_number}] BŁĄD: Wpisywanie PINu: {e}")
            return
        time.sleep(1)
        try:
            enter_pin_button_locator = (By.CSS_SELECTOR, "button[data-functional-selector='join-game-pin']")
            enter_pin_button = wait.until(EC.element_to_be_clickable(enter_pin_button_locator))
            enter_pin_button.click()
            # print(f"[Instancja {instance_display_number}] Przycisk 'Wprowadź' (PIN) kliknięty.")
        except TimeoutException:
            print(f"[Instancja {instance_display_number}] BŁĄD: Przycisk 'Wprowadź' (PIN) nie znaleziony (timeout).")
            return
        except Exception as e:
            print(f"[Instancja {instance_display_number}] BŁĄD: Klikanie 'Wprowadź' (PIN): {e}")
            return
        time.sleep(1)
        try:
            nickname_input_locator = (By.ID, "nickname")
            nickname_input_field = wait.until(EC.element_to_be_clickable(nickname_input_locator))
            nickname_input_field.send_keys(unique_nickname)
            # print(f"[Instancja {instance_display_number}] Pseudonim '{unique_nickname}' wpisany.")
        except TimeoutException:
            print(f"[Instancja {instance_display_number}] BŁĄD: Pole Pseudonim nie znalezione (timeout).")
            return
        except Exception as e:
            print(f"[Instancja {instance_display_number}] BŁĄD: Wpisywanie Pseudonimu: {e}")
            return
        time.sleep(1)
        try:
            join_button_locator = (By.CSS_SELECTOR, "button[data-functional-selector='join-button-username']")
            join_button = wait.until(EC.element_to_be_clickable(join_button_locator))
            join_button.click()
            print(f"[Instancja {instance_display_number}] Bot '{unique_nickname}' dołączył (PIN: {game_pin}).")
        except TimeoutException:
            print(f"[Instancja {instance_display_number}] BŁĄD: Przycisk 'OK, zaczynajmy!' nie znaleziony (timeout).")
            return
        except Exception as e:
            print(f"[Instancja {instance_display_number}] BŁĄD: Klikanie 'OK, zaczynajmy!': {e}")
            return

    except Exception as e_global:
        print(f"[Instancja {instance_display_number}] BŁĄD GLOBALNY: {e_global}")


def close_driver_in_thread(driver_instance, instance_number):
    try:
        driver_instance.quit()
    except Exception as e:
        print(f"[Zamykanie {instance_number}] BŁĄD: {e}")

if __name__ == "__main__":
    setup_screen_geometry() # Ustaw globalne wymiary przed pętlą

    launch_threads = []
    number_of_instances = 20 # Możesz ustawić więcej, np. 10, aby zobaczyć 2 rzędy

    print(f"Uruchamianie {number_of_instances} instancji...")

    for i in range(number_of_instances): # i będzie od 0 do number_of_instances - 1
        thread = threading.Thread(target=open_kahoot_in_thread, args=(i,)) # Przekaż i jako instance_number_zero_indexed
        launch_threads.append(thread)
        thread.start()
        time.sleep(3) # Krótkie opóźnienie, aby system nadążył, można dostosować

    for thread in launch_threads:
        thread.join()

    with lock:
        num_active = len(active_drivers)

    if num_active > 0:
        print(f"\n{num_active} instancji działa. Przeglądarki pozostaną otwarte.")
        input("Naciśnij Enter, aby zamknąć wszystkie...")

        closing_threads = []
        with lock:
            drivers_to_close = list(active_drivers)
            active_drivers.clear()

        for i, driver_instance in enumerate(drivers_to_close):
            close_thread = threading.Thread(target=close_driver_in_thread, args=(driver_instance, i+1))
            closing_threads.append(close_thread)
            close_thread.start()

        for thread in closing_threads:
            thread.join()
        print("Wszystkie instancje zamknięte.")
    else:
        print("\nNie uruchomiono żadnej instancji lub wystąpiły błędy podczas uruchamiania.")

    print("\nSkrypt zakończony.")