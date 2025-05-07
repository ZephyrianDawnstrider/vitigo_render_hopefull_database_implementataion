<configuration>
  <system.webServer>
    <handlers>
      <add name="PythonHandler" path="handler.fcgi" verb="*" modules="FastCgiModule"
           scriptProcessor="C:\Users\Ayush\AppData\Local\Programs\Python\Python313\python.exe|C:\Users\Ayush\AppData\Local\Programs\Python\Python313\Lib\site-packages\wfastcgi.py"
           resourceType="Unspecified" requireAccess="Script" />
    </handlers>
    <defaultDocument>
      <files>
        <add value="handler.fcgi" />
      </files>
    </defaultDocument>
  </system.webServer>
</configuration>
