all:server-działanie.pdf

server-działanie.pdf:server-działanie.tex DiagramKlas.pdf
	pdflatex server-działanie.tex
	pdflatex server-działanie.tex

DiagramKlas.eps:DiagramKlas.dia
	dia --export DiagramKlas.eps DiagramKlas.dia

DiagramKlas.pdf:DiagramKlas.eps
	epstopdf DiagramKlas.eps

.PHONY:all
