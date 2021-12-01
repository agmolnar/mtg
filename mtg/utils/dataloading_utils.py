import pandas as pd
import numpy as np
import re
from mtg.preprocess.seventeenlands import clean_bo1_games

def load_data(filename, cards, name=None):
    if name == "draft":
        return load_draft_data(filename, cards)
    elif name == "bo1":
        return load_bo1_data(filename, cards)
    else:
        return pd.read_csv(filename)

def sort_cols_by_card_idxs(df, card_col_prefixes, cards):
    #initialize columns to start with the non-card columns
    column_order = [c for c in df.columns if not any([c.startswith(prefix) for prefix in card_col_prefixes])]
    card_names = cards.sort_values(by="idx",ascending=True)['name'].tolist()
    for prefix in card_col_prefixes:
        prefix_columns = [prefix + "_" + name for name in card_names]
        column_order += prefix_columns
    #reorder dataframe to abide by new column ordering
    #   this is just so df[self.deck_cols].to_numpy() 
    #   yields a comparable matrix to df[self.sideboard_cols].to_numpy() 
    df = df[column_order]
    return df

def load_bo1_data(filename, cards):
    df = pd.read_csv(
        data_file,
        usecols=lambda x: x not in ["opp_rank"],
        dtype={
        'draft_id':str,
        'rank':str,
        'opp_rank':str,
        'main_colors':str,
        'splash_colors':str,
        'opp_colors':str,
        },
        na_filter=False,
    )
    #lower case makes our life easier
    df.columns = [x.lower() for x in df.columns]
    df = clean_bo1_games(
        df,
        cards,
        drop_cols=['expansion','event_type','game_number'],
        rename_cols={'draft_time':'date'}
    )
    df['date'] = pd.to_datetime(df['date'])
    card_col_prefixes = ['deck','opening_hand','drawn','sideboard']
    df = sort_cols_by_card_idxs(df, card_col_prefixes, cards)
    return df

def load_draft_data(filename, cards):
    COLUMN_REGEXES = {
        re.compile(r'user_match_win_rate_bucket'): 'float16',
        re.compile(r'user_n_matches_bucket'): 'int8',
        re.compile(r'user_rank'): 'str',
        re.compile(r'draft_id'): 'str',
        re.compile(r'draft_time'): 'str',
        re.compile(r'expansion'): 'str',
        re.compile(r'event_type'): 'str',
        re.compile(r'event_match_wins'): 'int8',
        re.compile(r'event_match_losses'): 'int8',
        re.compile(r'pack_number'): 'int8',
        re.compile(r'pick_number'): 'int8',
        re.compile(r'pick$'): 'str',
        re.compile(r'pick_maindeck_rate'): 'float16',
        re.compile(r'pick_sideboard_in_rate'): 'float16',

        re.compile(r'pool_.*'): 'int8',
        re.compile(r'pack_card_.*'): 'int8',
    }
    col_names = pd.read_csv(filename, nrows=0).columns
    data_types = {}
    draft_cols = []
    for c in col_names:
        if c.startswith("pack_card_"):
            draft_cols.append(c)
        elif c == "pick":
            draft_cols.append(c)
        elif c.startswith("pool_"):
            draft_cols.append(c)
        for (r, t) in COLUMN_REGEXES.items():
            if r.match(c):
                data_types[c] = t

    df = pd.read_csv(
        filename,
        dtype=data_types,
        usecols=[
            'draft_id',
            'draft_time',
            'event_match_losses',
            'event_match_wins',
            'pack_number',
            'pick_number',
            'user_n_matches_bucket',
            'user_match_win_rate_bucket',
            'user_rank'
            # ...
        ] + draft_cols
    )
    rename_cols = {'user_rank':'rank', 'user_match_win_rate_bucket':'user_win_rate_bucket', 'draft_time':'date'}
    df.columns = [x.lower() if x not in rename_cols else rename_cols[x] for x in df.columns]
    n_picks = df.groupby("draft_id")["pick"].count()
    t = n_picks.max()
    bad_draft_ids = n_picks[n_picks < t].index.tolist()
    df = df[~df['draft_id'].isin(bad_draft_ids)]
    name_to_idx_mapping = {k.split("//")[0].strip().lower():v for k,v in cards.set_index('name')['idx'].to_dict().items()}
    df['pick'] = df['pick'].str.lower().apply(lambda x: name_to_idx_mapping[x])
    df['date'] = pd.to_datetime(df['date'])
    df['won'] = (df['event_match_wins']/(df['event_match_wins'] + df['event_match_losses'])).fillna(0.0)
    card_col_prefixes = ['pack_card','pool']
    df = sort_cols_by_card_idxs(df, card_col_prefixes, cards)
    df['position'] = df['pack_number'] * (df['pick_number'].max() + 1) + df['pick_number']
    df = df.sort_values(by=['draft_id','position'])
    return df
