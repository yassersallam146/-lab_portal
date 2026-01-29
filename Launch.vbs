Set WshShell = CreateObject("WScript.Shell")
' تشغيل ملف الـ bat في وضعية الإخفاء التام (الرقم 0 يعني مخفي)
WshShell.Run chr(34) & "Start_Lab.bat" & chr(34), 0
Set WshShell = Nothing