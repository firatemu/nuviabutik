"""
Download Views - NuviaButik Downloads
"""

from django.http import HttpResponse, Http404, FileResponse
from django.shortcuts import render
from django.conf import settings
import os
from pathlib import Path

# Bu app artık Print Agent indirme için kullanılmıyor
# Local Print Agent kullanıldığı için sunucu tabanlı indirme kaldırıldı