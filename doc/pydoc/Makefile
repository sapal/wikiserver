all:fileManager.html helper.html hiddenServer.html hsConnection.html httpServer.html server.html config.html

%.html:../../code/%.py
	cd ../../code ; pydoc -w $*
	mv ../../code/$@ .

.PHONY:all

