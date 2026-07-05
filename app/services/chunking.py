class RecursiveChunker:
    def __init__(self,chunk_size=509 , overlap=90):
        self.chunk_size=chunk_size
        self.overlap=overlap
        self.seperators=["\n\n","\n", ". ", " ", ""]
    
    def chunk_creater(self,text:str,seperator_index):
         #BASE CASE 1: text already chota hai, split karne ki zarurat nahi
        if len(text) <= self.chunk_size:
            return [text]
        # BASE CASE 2: saare separators khatam ho gaye, ab aur split nahi kar sakte
        if seperator_index >= len( self.seperators):
            return [text]   
        current_seperator=self.seperators[seperator_index]
        pieces=text.split(current_seperator)

        result=[]
        for piece in pieces:
            if not piece.strip():  
                continue
            if len(piece)>self.chunk_size:
                sub_pieces=self.chunk_creater(piece,seperator_index+1)
                result.extend(sub_pieces)
            else:
                result.append(piece)#kyuki ye ek baar me hogya all chunks are kept as lists in result
        return result
    
    #now for calling above method + overlap creation

    def chunking(self,text:str):
       
        raw_chunks = self.chunk_creater(text, 0)
        final_chunks = []
    
        for i in range(len(raw_chunks)):
            chunk = raw_chunks[i]
            if i != 0:
                chunk = raw_chunks[i-1][-self.overlap:] + " " + chunk
            final_chunks.append(chunk)
    
        return final_chunks

chunker = RecursiveChunker()
