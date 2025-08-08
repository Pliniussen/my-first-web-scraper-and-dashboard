# -*- coding: utf-8 -*-
"""
Created on Tue Dec 19 12:45:30 2023

@author: plini
"""

#%%

# LOAD NECESSARY MODULES

from artist_scraper import artist_name
from  dash import html, dcc, Dash, ctx
from dash.dependencies import Input, Output
from dash_holoniq_wordcloud import DashWordcloud
import pandas as pd
import plotly.express as px

#%%

# CHOOSE FOLDER TO READ CSV FILE
df = pd.read_csv(f'{artist_name}/concerts.csv')

# REMOVE IT'S TIME TOUR FROM DATAFRAME
df = df[df['tour'] != "It's Time"]

def create_song_list(df):
    
    # CREATE A SONG_DICT AND GET SONG_COLUMN CONTENT
    song_dict = {}
    song_column = df['songs']

    # ITERATE THROUGH EACH ROW IN COLUMN AND SPLIT STRING INTO LIST
    for string in song_column:
        songs = string.split(', ')
        
        # ITERATE THROUGH EACH SONG IN THE LIST AND SKIP IF NO SETLIST
        for song in songs:
            if song != 'NO SETLIST INFORMATION':
                
                # APPEND SONG TO DICTIONARY AND INCREMENT VALUE + 1
                song_dict[song] = song_dict.get(song, 0) + 1
    
    # MAKE THE DICTIONARY INTO A LIST OF LISTS AND SORT IT BY DICT VALUE
    song_list = [[song, count] for song, count in song_dict.items()]
    song_list = sorted(song_list, key=lambda song: song[1], reverse=True)
    
    return song_list

# FUNCTION TO NORMALISE WORD CLOUD DATA (COPY-PASTED FROM MODULE DOCUMENTATION)
def normalise(lst, vmax=75, vmin=24):
    lmax = max(lst, key=lambda x: x[1])[1]
    lmin = min(lst, key=lambda x: x[1])[1]
    vrange = vmax-vmin
    lrange = lmax-lmin or 1
    for entry in lst:
        entry[1] = int(((entry[1] - lmin) / lrange) * vrange + vmin)
    return lst

# CALL CREATE_SONG_LIST() AND NORMALISE() FUNTIONS ON DATAFRAME TO CREATE SONG LIST
song_list = normalise(create_song_list(df))

def create_venue_fig(df):
    
    # SPLIT ALL ENTRIES IN SONGS COLUMN, OVERWRITE EXISTING COLUMN AND EXPLODE
    df_exploded = df.assign(songs=df['songs'].str.split(',')).explode('songs')
    
    # GROUP THE SONGS FOR EACH UNIQUE VENUE
    df_grouped = df_exploded.groupby('venue')['songs']
    
    # COUNT THE SONGS IN EACH VENUE AND RESET INDEX
    venue_count = df_grouped.count().reset_index(name='venue_count')
    
    # MERGE NEW DATAFRAME WITH THE OLD
    df_merged = pd.merge(df, venue_count, on='venue')

    # CREATE VENUE FIGURE
    fig = px.scatter_geo(df_merged,    
        lat=df_merged['latitude'],
        lon=df_merged['longitude'],
        size='venue_count',
        hover_name='venue',
        color_discrete_sequence=["blue"], 
        opacity=0.5,
        height=400,
        size_max=25,
        title='Venue Frequency Map',
    )
    
    # UPDATE VENUE MAP LAYOUT
    fig.update_geos(
        projection_type="mt flat polar quartic",
        showcoastlines=True, coastlinecolor="Black",
        showland=True,
        landcolor="light blue",
    )
    
    # UPDATE VENUE MAP MARGIN
    fig.update_layout(
        margin={"r":0,"t":50,"l":0,"b":0},
    )
    
    return fig    

# CALL THE CREATE_VENUE_FIG() FUNCTION
venue_fig = create_venue_fig(df)

def create_bar_chart():
   
    # CREATE AN EMPTY BAR CHART
    fig = px.bar(title='Setlist Placement Frequency')
    
    # UPDATE BAR CHART LAYOUT
    fig.update_layout(
        xaxis={'visible': True, 'showticklabels': False},
        yaxis={'visible': True, 'showticklabels': False}
    )
    
    return fig

# CALL THE CREATE_BAR_CHART() FUNCTION
bar_chart = create_bar_chart()

# INITIALISE THE APP
app = Dash(__name__)

# APP LAYOUT
app.layout = html.Div([
    
    # CREATE HEADER
    html.H1('IMAGINE DRAGONS', style={'textAlign': 'center'}),
    
    # CREATE SUBHEADER
    html.H2('Concert Analysis Dashboard', style={'textAlign': 'center'}),
    
    # CREATE LINE
    html.Hr(),
        
    # CREATE WORD CLOUD INPUT
    dcc.Input(
        id='word-cloud-input',
        placeholder='Enter a value...',
        type='text',
        value='',
    ),
    
    # CREATE TOUR DROPDOWN
    dcc.Dropdown(
        id='tour-dropdown',
        options=[
            {'label': 'All Tours', 'value': 'all'}
            ] + [
            {'label': tour, 'value': tour} 
            for tour in sorted(df['tour'].unique())
        ],
        value='all',
        multi=True,
    ),
    
    html.Div(style={'margin': 'auto',
                    'display': 'flex',
                    'justifyContent': 'space-between'}, children=[

        # CREATE WORD CLOUD
        DashWordcloud(
            id='word-cloud',
            list=song_list,
            width=800, height=400,
            gridSize=16,
            color='random-dark',
            backgroundColor='#E5ECF6',
            shuffle=False,
            rotateRatio=0.5,
            shrinkToFit=True,
            hover=True
        ),
    
        # CREATE VENUE MAP
        dcc.Graph(
            id='venue-map',
            figure = venue_fig,
            style={'width': '75%'}
        )
    ]),
    
    # CREATE BAR CHART
    dcc.Graph(
        id='bar-chart',
        figure = bar_chart,    
    ),
    
    # CREATE RESET BUTTON
    html.Button(
        id='reset-button',
        children='Reset Button',
        n_clicks=0,
        style={'margin': 'auto', 'display': 'flex'}
    ),
])
    
# CALLBACK TAKES INPUT FROM DROPDOWN AND INPUT AND OUTPUTS IT TO WORD CLOUD
@app.callback(
    Output(component_id='word-cloud', component_property='list'),
    Input(component_id='tour-dropdown', component_property='value'),
    Input(component_id='word-cloud-input', component_property='value')
)

def update_cloud(selected_tours, input_value):
    
    # IF NO TOUR IS SELECTED RETURN EMPTY LIST
    if not selected_tours:
        return []
    
    # IF ALL TOURS ARE SELECTED MAKE NO CHANGE TO THE DATAFRAME
    if 'all' in selected_tours:
        updated_df = df
        
    # ELSE CHANGE THE DATAFRAME TO ONLY INCLUDE SELECTED TOURS
    else:
        updated_df = df[df['tour'].isin(selected_tours)]
        
    # CALL CREATE_SONG_LIST() FUNCTION ON UPDATED DATAFRAME
    updated_song_list = create_song_list(updated_df)
    
    # CALL NORMALISE() FUNTION TO NORMALISE THE UPDATED SONG LIST
    normalised_song_list = normalise(updated_song_list)
    
    # TRY TO MAKE THE WORD_CLOUD INPUT INTO AN INTEGER
    try:
        input_value = int(input_value)
        
        # IF SUCCESSFUL SLICE NORMALISED SONG LIST AT INPUT_VALUE
        finished_output = normalised_song_list[0:input_value]
        return finished_output
    
    # IF INPUT IS NOT AN INTEGER RETURN THE NON-SLICED NORMALISED SONG LIST
    except ValueError:
        return normalised_song_list
    
# CALLBACK TAKES INPUT FROM WORD CLOUD AND RESET BUTTON AND OUTPUTS IT TO VENUE MAP
@app.callback(
    Output('venue-map', 'figure'),
    Input('word-cloud', 'click'),
    Input('reset-button', 'n_clicks')
)

def update_venue(click, n_clicks):

    # FIND THE ID OF THE TRIGGERED CLICK EVENT
    triggered_id = ctx.triggered_id
    
    # IF RESET BUTTON TRIGGERED RETURN OLD VENUE FIGURE
    if triggered_id == 'reset-button' and n_clicks:
        return venue_fig
        
    # IF WORD CLOUD TRIGGERED AND CLICK IS NOT NONE
    if triggered_id == 'word-cloud' and click != None:
    
        # ISOLATE SONG NAME BY TAKING INDEX ZERO OF CLICK EVENT
        clicked_song = click[0]
        
        # SPLIT ALL ENTRIES IN SONGS COLUMN, OVERWRITE EXISTING COLUMN AND EXPLODE
        df_exploded = df.assign(songs=df['songs'].str.split(',')).explode('songs')
        
        # FOR EACH UNIQUE VENUE GROUP ALL ROWS CONTAINING THE CLICKED SONG
        df_grouped = df_exploded[df_exploded['songs'].str.contains(clicked_song, regex=False)].groupby('venue')
        
        # COUNT THE SONGS IN EACH VENUE AND RESET INDEX
        venue_count = df_grouped.size().reset_index(name='venue_count')
        
        # MERGE NEW DATAFRAME WITH THE OLD
        df_merged = pd.merge(df, venue_count, on='venue')
        
        # CREATE NEW VENUE FIGURE
        fig = px.scatter_geo(df_merged,    
            lat=df_merged['latitude'],
            lon=df_merged['longitude'],
            size='venue_count',
            hover_name='venue',
            color_discrete_sequence=["green"], 
            opacity=0.5,
            height=400,
            size_max=10,
            title=f'Venue Frequency Map for: <i><b>{clicked_song}</b></i>'
        )
        
        # UPDATE LAYOUT OF NEW VENUE FIGURE
        fig.update_geos(
            projection_type="mt flat polar quartic",
            showcoastlines=True, coastlinecolor="Black",
            showland=True,
            landcolor="light blue"
        )       
        
        # UPDATE VENUE MAP MARGIN
        fig.update_layout(
            margin={"r":0,"t":50,"l":0,"b":0}
        )
        
        return fig
    
    # IF NO CLICK EVEN HAPPENS OUTPUT OLD VENUE FIGURE
    else:
        return venue_fig
    

# CALLBACK TAKES INPUT FROM WORD CLOUD AND RESET BUTTON AND OUTPUTS IT TO BAR CHART
@app.callback(
    Output('bar-chart', 'figure'),
    Input('word-cloud', 'click'),
    Input('reset-button', 'n_clicks')
)

def update_bar_chart(click, n_clicks):
    
    # FIND THE ID OF THE TRIGGERED CLICK EVENT
    triggered_id = ctx.triggered_id
    
    # IF RESET BUTTON TRIGGERED RETURN OLD BAR CHART
    if triggered_id == 'reset-button' and n_clicks:
        return bar_chart
        
    # IF WORD CLOUD TRIGGERED AND CLICK IS NOT NONE
    if triggered_id == 'word-cloud' and click != None:

        # ISOLATE SONG NAME BY TAKING INDEX ZERO OF CLICK EVENT, ASSIGN TO NEW VARIABLE
        clicked_song = click[0]
        song = clicked_song
        
        # CREATE A POSITION_DICT AND GET SONG_COLUMN CONTENT
        position_dict = {}
        song_column = df['songs']
        
        # ITERATE THROUGH EACH ROW IN COLUMN
        for string in song_column:
            
            # SPLIT STRING INTO LIST
            songs = string.split(', ')
            
            # IF THE CLICKED SONG IS IN THE LIST
            if song in songs:
                
                # LOCATE ITS INDEX NUMBER AND INCREMENT INDEX + 1
                position = songs.index(song) + 1
                
                # APPEND POSITION TO DICTIONARY AND INCREMENT VALUE + 1
                position_dict[position] = position_dict.get(position, 0) + 1
                
        # CREATE DATAFRAME FROM POSITION DICTIONARY
        position_data = pd.DataFrame(list(position_dict.items()),
                                     columns=['Position', 'Frequency'])
        
        # CREATE NEW BAR CHART WITH POSITION DATA
        fig = px.bar(position_data,
            x='Position', y='Frequency',
            title=f'Setlist Placement Frequency for: <i><b>{song}</b></i>',
            color= 'Frequency',
            color_continuous_scale='viridis'
        )
        
        return fig
    
    # IF NO CLICK EVEN HAPPENS OUTPUT OLD VENUE FIGURE
    else:
        return bar_chart
    
# RUN THE APP
if __name__ == '__main__':
    app.run_server(debug=True, port=8050)

print('Running at http://127.0.0.1:8050/')


#%%
