import asyncio
import random

from kahoot import KahootClient # Upewnij się, że to poprawny import dla Twojej biblioteki
from kahoot.packets.impl.respond import RespondPacket
from kahoot.packets.server.game_over import GameOverPacket
from kahoot.packets.server.game_start import GameStartPacket
from kahoot.packets.server.question_end import QuestionEndPacket
from kahoot.packets.server.question_ready import QuestionReadyPacket
from kahoot.packets.server.question_start import QuestionStartPacket

async def handle_game_start(packet: GameStartPacket, bot_name: str):
    # Ten handler jest dobrym miejscem na potwierdzenie, że bot dołączył i gra się zaczyna
    print(f"[{bot_name}] Pomyślnie dołączono i gra rozpoczęta! Tryb gry: {packet.game_mode}")

async def handle_game_over(packet: GameOverPacket, bot_name: str):
    print(f"[{bot_name}] Koniec gry. Miejsce: {packet.rank}, Łączny wynik: {packet.total_score}")

async def handle_question_start(packet: QuestionStartPacket, client_instance: KahootClient, bot_name: str):
    question_index_display = packet.game_block_index + 1
    print(f"[{bot_name}] Pytanie {question_index_display} rozpoczęte. Typ: {packet.game_block_type}, Liczba opcji: {len(packet.choices)}")

    choice_index_to_send = random.randint(0, 3) # Zakładamy 4 opcje (0-3)

    await asyncio.sleep(0.5)
    try:
        await client_instance.send_packet(RespondPacket(client_instance.game_pin, choice_index_to_send, packet.game_block_index))
        print(f"[{bot_name}] Odpowiedź na pytanie {question_index_display} wysłana (opcja: {choice_index_to_send}).")
    except Exception as e:
        print(f"[{bot_name}] BŁĄD przy wysyłaniu odpowiedzi na pytanie {question_index_display}: {e}")

async def handle_question_end(packet: QuestionEndPacket, bot_name: str):
    question_info = ""
    if hasattr(packet, 'question_index'):
        question_info = f"Pytanie {packet.question_index + 1} zakończone. "

    print(f"[{bot_name}] {question_info}Poprawne odpowiedzi: {packet.correct_answers}, Zdobyte punkty: {packet.points}")

async def handle_question_ready(packet: QuestionReadyPacket, bot_name: str):
    print(f"[{bot_name}] Gotowość na pytanie {packet.question_index + 1}.")

async def run_single_bot(game_pin: int, bot_base_name: str, bot_number: int):
    client = KahootClient()
    bot_name = f"{bot_base_name} {bot_number}"

    # Rejestracja handlerów
    client.on("game_start", lambda packet: handle_game_start(packet, bot_name))
    client.on("game_over", lambda packet: handle_game_over(packet, bot_name))
    client.on("question_start", lambda packet: handle_question_start(packet, client, bot_name))
    client.on("question_end", lambda packet: handle_question_end(packet, bot_name))
    client.on("question_ready", lambda packet: handle_question_ready(packet, bot_name))

    try:
        print(f"[{bot_name}] Próba dołączenia do gry {game_pin}...")
        # Jeśli `join_game` jest blokujące i utrzymuje połączenie,
        # ta korutyna "zawiśnie" tutaj na czas gry.
        # Handlery zdarzeń będą wywoływane przez pętlę zdarzeń asyncio.
        await client.join_game(game_pin, bot_name)
        # Poniższy print prawdopodobnie się nie wykona, jeśli `join_game` jest długotrwałe.
        # Potwierdzenie dołączenia powinno przyjść z eventu (np. obsłużone w handle_game_start).
        # print(f"[{bot_name}] Linia po `await client.join_game` (może się nie wykonać).")
    except asyncio.CancelledError:
        print(f"[{bot_name}] Zadanie dołączenia anulowane.") # Obsługa, gdyby task był anulowany
    except Exception as e:
        print(f"[{bot_name}] BŁĄD podczas `join_game` lub rozłączenie: {e}")
    finally:
        # Można by tu dodać logikę czyszczenia, np. client.close(), jeśli biblioteka tego wymaga
        # print(f"[{bot_name}] Zakończono działanie korutyny run_single_bot.")
        pass


async def main():
    while True:
        game_pin_str = input("Podaj PIN gry: ")
        if game_pin_str.isdigit():
            game_pin = int(game_pin_str)
            break
        else:
            print("Nieprawidłowy PIN. PIN powinien składać się tylko z cyfr.")

    while True:
        num_bots_str = input("Podaj liczbę botów do uruchomienia: ")
        if num_bots_str.isdigit() and int(num_bots_str) > 0:
            number_of_bots = int(num_bots_str)
            break
        else:
            print("Nieprawidłowa liczba botów. Podaj dodatnią liczbę całkowitą.")

    bot_base_name_input = input("Podaj bazową nazwę dla botów (np. Ben): ")
    if not bot_base_name_input.strip():
        bot_base_name_input = "Bot"
        print(f"Użyto domyślnej nazwy bazowej: '{bot_base_name_input}'")

    print(f"\nInicjowanie {number_of_bots} botów o nazwach '{bot_base_name_input} X' (pojedynczo)...")

    active_bot_tasks = []

    for i in range(number_of_bots):
        bot_number = i + 1
        print(f"\n--- Inicjowanie bota: {bot_base_name_input} {bot_number} ---")

        # Tworzymy zadanie dla każdego bota. Rozpocznie ono próbę dołączenia w tle.
        task = asyncio.create_task(run_single_bot(game_pin, bot_base_name_input, bot_number))
        active_bot_tasks.append(task)

        # Czekamy chwilę, aby dać czas na zainicjowanie dołączenia przez bieżącego bota,
        # zanim zaczniemy inicjować następnego. To sprawi, że boty będą *zaczynały* dołączać
        # pojedynczo na liście graczy.
        print(f"Bot {bot_base_name_input} {bot_number} uruchomiony w tle. Czekanie na następnego...")
        if i < number_of_bots - 1: # Nie czekaj po ostatnim bocie
            # Ten `sleep` kontroluje, jak szybko *inicjujemy* kolejne boty.
            # Dostosuj tę wartość, aby uzyskać pożądany efekt pojawiania się botów.
            await asyncio.sleep(0.2) # np. 2 sekundy przerwy między inicjacjami

    print(f"\nProces inicjowania {number_of_bots} botów zakończony.")
    print("Boty są teraz aktywne i oczekują na zdarzenia z gry.")
    print("Naciśnij Ctrl+C, aby zakończyć wszystkie boty.")

    # Czekamy na zakończenie wszystkich zadań botów.
    # Zakończą się one, gdy ich korutyny `run_single_bot` się zakończą
    # (np. po otrzymaniu `game_over` i zakończeniu `await client.join_game`, lub po błędzie).
    if active_bot_tasks:
        await asyncio.gather(*active_bot_tasks, return_exceptions=True)

    print("\nWszystkie zadania botów zostały zakończone.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWykonanie przerwane przez użytkownika.")
    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd w głównym wykonaniu: {e}")
