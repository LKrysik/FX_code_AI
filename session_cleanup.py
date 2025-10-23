#!/usr/bin/env python3
"""
Session Cleanup Service
Automatyczne czyszczenie starych sesji w folderze data/
"""

import sys
import os

from typing import Optional, Any
# Fix Windows console encoding issues
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # For older Python versions
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

import shutil
import glob
import time
import logging
from pathlib import Path

# Konfiguracja
DATA_DIR = "data"
KEEP_SESSIONS = 20  # Zachowaj ostatnie 20 sesji
CHECK_INTERVAL = 10  # Sprawdzaj co godzinę (3600 sekund)

# Safe print function for Unicode handling
def safe_print(*args, **kwargs):
    """Bezpieczne drukowanie z obsługą błędów Unicode"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Replace problematic Unicode characters with ASCII alternatives
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_arg = (arg.replace('\u2713', '[OK]')
                              .replace('\u2717', '[FAIL]')
                              .replace('\u2022', '*')
                              .replace('📊', '[STATS]')
                              .replace('⚠️', '[WARNING]')
                              .replace('✅', '[SUCCESS]')
                              .replace('❌', '[ERROR]'))
                safe_args.append(safe_arg)
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)

# Custom logging handler that handles Unicode safely
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Fallback to ASCII representation
            record.msg = str(record.msg).encode('ascii', errors='replace').decode('ascii')
            super().emit(record)

# Logging configuration with Unicode support
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('session_cleanup.log', encoding='utf-8'),
        SafeStreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_expired_sessions(event_bus: Optional[Any] = None):
    """Usuwa stare sesje, zachowując tylko najnowsze"""
    try:
        if not os.path.exists(DATA_DIR):
            logger.warning(f"Folder {DATA_DIR} nie istnieje")
            return
        
        # Znajdź wszystkie foldery sesji
        session_pattern = os.path.join(DATA_DIR, "session_*")
        session_dirs = glob.glob(session_pattern)
        
        if not session_dirs:
            logger.info("Nie znaleziono sesji do czyszczenia")
            return
        
        # Sortuj według czasu modyfikacji (najnowsze pierwsze)
        session_dirs.sort(key=os.path.getmtime, reverse=True)
        
        total_sessions = len(session_dirs)
        logger.info(f"Znaleziono {total_sessions} sesji")
        
        if total_sessions <= KEEP_SESSIONS:
            logger.info(f"Liczba sesji ({total_sessions}) <= {KEEP_SESSIONS}, nie ma co usuwać")
            return
        
        # Usuń stare sesje
        sessions_to_remove = session_dirs[KEEP_SESSIONS:]
        removed_count = 0
        
        for session_dir in sessions_to_remove:
            try:
                # Sprawdź rozmiar przed usunięciem
                size_mb = get_folder_size(session_dir) / (1024 * 1024)
                
                shutil.rmtree(session_dir)
                removed_count += 1
                
                if event_bus:
                    session_id = os.path.basename(session_dir)
                    event_bus.publish('session.cleaned', {
                        'session_id': session_id,
                        'reason': 'expired',
                        'size_mb': size_mb
                    })

                logger.info(f"Usunięto sesję: {os.path.basename(session_dir)} ({size_mb:.1f} MB)")
                
                # Przerwa co 10 sesji żeby nie obciążać systemu
                if removed_count % 10 == 0:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Błąd usuwania {session_dir}: {e}")
        
        logger.info(f"Czyszczenie zakończone: usunięto {removed_count} sesji, pozostało {total_sessions - removed_count}")
        
    except Exception as e:
        logger.error(f"Błąd podczas czyszczenia sesji: {e}")

def get_folder_size(folder_path):
    """Oblicza rozmiar folderu w bajtach"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except (OSError, IOError, PermissionError) as e:
        logger.warning(f"Nie można obliczyć rozmiaru dla {folder_path}: {e}")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd obliczania rozmiaru dla {folder_path}: {e}")
    return total_size

def get_sessions_stats():
    """Zwraca statystyki sesji"""
    try:
        if not os.path.exists(DATA_DIR):
            return {"count": 0, "total_size_mb": 0}
        
        session_dirs = glob.glob(os.path.join(DATA_DIR, "session_*"))
        total_size = 0
        
        for session_dir in session_dirs:
            total_size += get_folder_size(session_dir)
        
        return {
            "count": len(session_dirs),
            "total_size_mb": total_size / (1024 * 1024)
        }
    except Exception as e:
        logger.error(f"Błąd pobierania statystyk: {e}")
        return {"count": 0, "total_size_mb": 0}

def safe_log_stats(message):
    """Bezpieczne logowanie statystyk z obsługą Unicode"""
    try:
        logger.info(message)
    except UnicodeEncodeError:
        # Replace Unicode characters with ASCII alternatives
        safe_message = (message.replace('📊', '[STATS]')
                               .replace('⚠️', '[WARNING]')
                               .replace('✅', '[SUCCESS]')
                               .replace('❌', '[ERROR]'))
        logger.info(safe_message)

def main(event_bus: Optional[Any] = None):
    """Główna pętla serwisu"""
    try:
        logger.info("Uruchomiono jednorazowe czyszczenie sesji...")
        logger.info(f"Folder danych: {DATA_DIR}")
        logger.info(f"Zachowywane sesje: {KEEP_SESSIONS}")
        
        stats_before = get_sessions_stats()
        safe_log_stats(f"[STATS] Stan początkowy: {stats_before['count']} sesji, {stats_before['total_size_mb']:.1f} MB")
        
        cleanup_expired_sessions(event_bus=event_bus)
        
        stats_after = get_sessions_stats()
        safe_log_stats(f"[STATS] Stan po czyszczeniu: {stats_after['count']} sesji, {stats_after['total_size_mb']:.1f} MB")
        logger.info("Czyszczenie zakończone.")
    except Exception as e:
        logger.error(f"Krytyczny błąd podczas uruchamiania serwisu: {e}")
        safe_print(f"[ERROR] Krytyczny błąd: {e}")

if __name__ == "__main__":
    main()