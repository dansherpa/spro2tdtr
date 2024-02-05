py -m build
py -m twine upload --repository pypi dist/spro2tdtr-0.0.11-*
py -m twine upload --repository pypi dist/spro2tdtr-0.0.11.*

REM python -m venv c:\dpk.test
REM do this
REM c:\dpk.test\Scripts\activate
REM python c:\dpk.test\Lib\site-packages\spro2tdtr\spro2tdtr.py
REM pip install spro2tdtr
REM REM pip install spro2tdtr --upgrade
REM deactivate
