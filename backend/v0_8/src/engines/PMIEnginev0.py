from tqdm import tqdm
tqdm.pandas()
import pandas as pd
import numpy as np

import joblib


from src.engines.Engine import CachedEngine
from src.engines.ngrams import Ngram

class PMIEngine(CachedEngine):
    def __init__(self, ID, name, params, cache_dir):
        super().__init__(ID, name, params, cache_dir)
        self.min_score = 0.
        self.max_score = 1.

        
    def _score_and_detail(self, dataset, round_to=3, **params):
        texts = dataset.segment(level="paragraph")
        self.pmi = PMI(texts)
        
        scores, details = self.typicality.process_objects(dataset.data.Texts)
        return scores, details

    
class PMI:
    def __init__(self, texts, **model_params):
        default_params = dict(ns=2, documents=texts, precompute_freqs=True)
        default_params.update(model_params)
        self.model = Ngram(**default_params)
        self.aggregate_func = np.mean
        
    def pmi(self, pair_str):
        w1, w2 = pair_str.split()
        return (
                self.model.prob(pair_str, log=True) - 
                (self.model.prob(w1, log=True) + 
                 self.model.prob(w2, log=True))
               )
    
    
    def process_object(self, row):
        pairs, pmis = [], []
        for text in row:
            cur_pairs = list(self.model.iter_ngrams(text, padding=False))
            pairs.extend(cur_pairs)
            pmis.extend(map(self.pmi, cur_pairs))
            
        return sorted(zip(pairs, pmis), key=lambda t:t[1]), self.aggregate_func(pmis)


    def process_objects(self, texts, round_to=3):
        tuples = texts.progress_apply(
#                        axis='columns', 
                        func=self.process_object
                )
        
        typs = tuples.apply(lambda t: t[1])
        typs = self.norm(typs).round(round_to)
        typs.name = "score"
        
        

        details = tuples.apply(lambda t: dict(t[0]))
        d = {k: v for smalld in tqdm(details, desc="constructing big d") for k, v in smalld.items()}
        values = np.asarray([d[k] for k in sorted(d.keys())]).round(round_to)
        values = self.norm(values, q=100)

        d = dict(zip(sorted(d.keys()), values))
        def swap_values(smalld):
            new_vals = sorted(((k, d[k]) for k in smalld), key=lambda t:t[1])
            top_pairs = 5
            return dict(new_vals[-top_pairs:])
        details = details.progress_apply(swap_values)
        details.name = "score_details"

        return typs, details

    
    def norm(self, v, map_to_positive=True):
        if map_to_positive:
            v = v+np.min(v)
        return v/np.sum(v)
    
    

        
        
