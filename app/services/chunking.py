class RecursiveChunker:
    def __init__(self,chunk_size=509 , overlap=100):
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


    #Updated chunking method so that we get consitent chunk size
    def chunking(self, text: str):
        raw_pieces = self.chunk_creater(text, 0)

        # chhote pieces ko merge kr rhe hai taaki har chunk chunk_size ke close ho
        merged_chunks = []
        current_chunk = ""

        for piece in raw_pieces:
            if len(current_chunk) + len(piece) + 1 <= self.chunk_size:
                current_chunk = (current_chunk + " " + piece).strip()
            else:
                if current_chunk:
                    merged_chunks.append(current_chunk)
                current_chunk = piece

        if current_chunk:
            merged_chunks.append(current_chunk)

        # STEP 2: overlap add
        final_chunks = []
        for i in range(len(merged_chunks)):
            chunk = merged_chunks[i]
            if i != 0:
                chunk = merged_chunks[i-1][-self.overlap:] + " " + chunk
            final_chunks.append(chunk)

        return final_chunks

chunker = RecursiveChunker()
