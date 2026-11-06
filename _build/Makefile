ARTIGO = tese


rt:
		pdflatex $(ARTIGO) 
clean:
	rm -f core *.core *.log *.aux *.toc *.lo[fpta] *.blg *.bbl \
	*.ind *.ilg *.idx *.glo *.gls *.out

bib:
		pdflatex $(ARTIGO)
		bibtex   $(ARTIGO)
		pdflatex $(ARTIGO)
		pdflatex $(ARTIGO)  
		pdflatex $(ARTIGO)  

