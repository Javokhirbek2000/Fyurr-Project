#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from enum import unique
import json
from operator import itemgetter
from os import abort
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from sqlalchemy.orm import backref
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
import re
from flask_migrate import Migrate, current
from flask_wtf import Form
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#
class Genre(db.Model):
    __tablename__ = 'Genre'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    
artist_genre_table = db.Table('artist_genre_table',
    db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True),
    db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), primary_key=True)
)

venue_genre_table = db.Table('venue_genre_table',
    db.Column('genre_id', db.Integer, db.ForeignKey('Genre.id'), primary_key=True),
    db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), primary_key=True)
)

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    genres = db.relationship('Genre', secondary=venue_genre_table, backref=db.backref('venues'))

    website_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))

    def __repr__(self):
        return f'<Venue {self.id} {self.name}>'


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    genres = db.relationship('Genre', secondary=artist_genre_table, backref=db.backref('artists'))
    
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))

    shows = db.relationship('Show', backref='artist', lazy=True)

    def __repr__(self):
        return f'<Artist {self.id} {self.name}>'
    
class Show(db.Model):
  __tablename__ = 'Show'

  id = db.Column(db.Integer, primary_key=True)
  starting_time = db.Column(db.DateTime, nullable=False)
  venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)

  def __repr__(self):
        return f'<Show {self.id} {self.starting_time} artist_id={self.artist_id} venue_id={self.venue_id}>'


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  venues = Venue.query.all()

  data = []
  cities_states = set()

  for venue in venues:
    cities_states.add((venue.city, venue.state))

  cities_states = list(cities_states)
  cities_states.sort(key=itemgetter(1,0))

  current_time = datetime.now()
  
  for loc in cities_states:
    venues_list = []
    for venue in venues:
      if (venue.city == loc[0]) and (venue.state == loc[1]):
        venue_shows = Show.query.filter_by(venue_id=venue.id).all()
        upcoming_count = 0
        for show in venue_shows:
          if show.starting_time > current_time:
            upcoming_count += 1

        venues_list.append({
          "id": venue.id,
          "name": venue.name,
          "num_upcoming_shows": upcoming_count
        }) 

    data.append({
            "city": loc[0],
            "state": loc[1],
            "venues": venues_list
        })

  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '').strip()

  venues = Venue.query.filter(Venue.name.ilike('%' + search_term + '%')).all()
  venue_list = []
  current_time = datetime.now()
  for venue in venues:
    venue_shows = Show.query.filter_by(venue_id=venue.id).all()
    upcoming_count = 0
    for show in venue_shows:
        if show.starting_time > current_time:
            upcoming_count += 1

    venue_list.append({
        "id": venue.id,
        "name": venue.name,
        "num_upcoming_shows": upcoming_count  
    })

  response = {
    "count": len(venues),
    "data": venue_list
  }

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = Venue.query.get(venue_id)
  
  if not venue:
    return redirect(url_for('index'))
  else:
    genres = [genre.name for genre in venue.genres]
    previous_shows = []
    previous_shows_count = 0
    upcoming_shows = []
    upcoming_shows_count = 0
    current_time = datetime.now()
    
    for show in venue.shows:
      if show.starting_time > current_time:
          upcoming_shows_count += 1
          upcoming_shows.append({
              "artist_id": show.artist_id,
              "artist_name": show.artist.name,
              "artist_image_link": show.artist.image_link,
              "starting_time": format_datetime(str(show.starting_time))
          })
      if show.starting_time < current_time:
          previous_shows_count += 1
          previous_shows.append({
              "artist_id": show.artist_id,
              "artist_name": show.artist.name,
              "artist_image_link": show.artist.image_link,
              "starting_time": format_datetime(str(show.starting_time))
          })
  
  
  data = {
          "id": venue_id,
          "name": venue.name,
          "genres": genres,
          "address": venue.address,
          "city": venue.city,
          "state": venue.state,
          "phone": (venue.phone[:3] + '-' + venue.phone[3:6] + '-' + venue.phone[6:]),
          "website": venue.website_link,
          "facebook_link": venue.facebook_link,
          "seeking_talent": venue.seeking_talent,
          "seeking_description": venue.seeking_description,
          "image_link": venue.image_link,
          "previous_shows": previous_shows,
          "previous_shows_count": previous_shows_count,
          "upcoming_shows": upcoming_shows,
          "upcoming_shows_count": upcoming_shows_count
        }
  
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  form = VenueForm()
  
  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  address = form.address.data.strip()
  phone = form.phone.data
  phone = re.sub('\D', '', phone) 
  genres = form.genres.data                 
  seeking_talent = True if form.seeking_talent.data == 'Yes' else False
  seeking_description = form.seeking_description.data.strip()
  image_link = form.image_link.data.strip()
  website_link = form.website_link.data.strip()
  facebook_link = form.facebook_link.data.strip()
   
  if not form.validate():
    flash( form.errors )
    return redirect(url_for('create_venue_submission'))

  else:
      insertion_error = False
      try:
          new_venue = Venue(name=name, city=city, state=state, address=address, phone=phone, \
              seeking_talent=seeking_talent, seeking_description=seeking_description, image_link=image_link, \
              website_link=website_link, facebook_link=facebook_link)
        
          for genre in genres:
            get_genre = Genre.query.filter_by(name=genre).one_or_none()
            if get_genre:
              new_venue.genres.append(get_genre)

            else:
              new_genre = Genre(name=genre)
              db.session.add(new_genre)
              new_venue.genres.append(new_genre)  

          db.session.add(new_venue)
          db.session.commit()
          
      except Exception as e:
          insertion_error = True
          print(f'Exception "{e}" happened while creating venue submission!')
          db.session.rollback()
          
      finally:
          db.session.close()

      if not insertion_error:
          flash('Venue ' + request.form['name'] + ' successfully created!')
          return redirect(url_for('index'))
      else:
          flash('ERROR!!!. Venue ' + name + ' could not be created!.')
          print("Error happened while creating venue submission")
          abort(500)

@app.route('/venues/<venue_id>', methods=['DELETE', 'GET'])
def delete_venue(venue_id):
  venue = Venue.query.get(venue_id)
  
  if not venue:
      return redirect(url_for('index'))
  else:
      deletion_error = False
      venue_name = venue.name
      
      try:
          db.session.delete(venue)
          db.session.commit()
      except:
          deletion_error = True
          db.session.rollback()
      finally:
          db.session.close()
          
      if deletion_error:
          flash(f'An error happened while deleting {venue_name}.')
          print("Error happened while deleting venue")
          abort(500)
      else:
          return jsonify({
              'deleted': True,
              'url': url_for('venues')
          })



#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.order_by(Artist.name).all()  

  results = []
  for artist in artists:
      results.append({
          "id": artist.id,
          "name": artist.name
      })
      
  return render_template('pages/artists.html', artists=results)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '').strip()
  artists = Artist.query.filter(Artist.name.ilike('%' + search_term + '%')).all()  
  artist_list = []
  current_time = datetime.now()
  
  for artist in artists:
      artist_shows = Show.query.filter_by(artist_id=artist.id).all()
      upcoming_count = 0
      
      for show in artist_shows:
          if show.starting_time > current_time:
              upcoming_count += 1

      artist_list.append({
          "id": artist.id,
          "name": artist.name,
          "num_upcoming_shows": upcoming_count  
      })

  response = {
      "count": len(artists),
      "data": artist_list
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = Artist.query.get(artist_id)   
  if not artist:
      return redirect(url_for('index'))
  else:
      genres = [ genre.name for genre in artist.genres ]
      previous_shows = []
      previous_shows_count = 0
      upcoming_shows = []
      upcoming_shows_count = 0
      current_time = datetime.now()
      
      for show in artist.shows:
          if show.starting_time > current_time:
              upcoming_shows_count += 1
              upcoming_shows.append({
                  "venue_id": show.venue_id,
                  "venue_name": show.venue.name,
                  "venue_image_link": show.venue.image_link,
                  "starting_time": format_datetime(str(show.starting_time))
              })
          if show.starting_time < current_time:
              previous_shows_count += 1
              previous_shows.append({
                  "venue_id": show.venue_id,
                  "venue_name": show.venue.name,
                  "venue_image_link": show.venue.image_link,
                  "starting_time": format_datetime(str(show.starting_time))
              })

      data = {
          "id": artist_id,
          "name": artist.name,
          "genres": genres,
          "city": artist.city,
          "state": artist.state,
          "phone": (artist.phone[:3] + '-' + artist.phone[3:6] + '-' + artist.phone[6:]),
          "website_link": artist.website_link,
          "facebook_link": artist.facebook_link,
          "seeking_venue": artist.seeking_venue,
          "seeking_description": artist.seeking_description,
          "image_link": artist.image_link,
          "past_shows": previous_shows,
          "past_shows_count": previous_shows_count,
          "upcoming_shows": upcoming_shows,
          "upcoming_shows_count": upcoming_shows_count
      }
      
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)  
  if not artist:
      return redirect(url_for('index'))
  else:
      form = ArtistForm(obj=artist)

  genres = [ genre.name for genre in artist.genres ]
  artist={
    "id": artist_id,
    "name": artist.name,
    "genres": genres,
    "city": artist.city,
    "state": artist.state,
    "phone": (artist.phone[:3] + '-' + artist.phone[3:6] + '-' + artist.phone[6:]),
    "website_link": artist.website_link,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  }

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  
  form = ArtistForm()

  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  phone = form.phone.data
  phone = re.sub('\D', '', phone) 
  genres = form.genres.data                
  seeking_venue = True if form.seeking_venue.data == 'Yes' else False
  seeking_description = form.seeking_description.data.strip()
  image_link = form.image_link.data.strip()
  website_link = form.website_link.data.strip()
  facebook_link = form.facebook_link.data.strip()

  if not form.validate():
      flash( form.errors )
      return redirect(url_for('edit_artist_submission', artist_id=artist_id))

  else:
      update_error = False
      try:
          artist = Artist.query.get(artist_id)
          artist.name = name
          artist.city = city
          artist.state = state
          artist.phone = phone
          artist.seeking_venue = seeking_venue
          artist.seeking_description = seeking_description
          artist.image_link = image_link
          artist.website_link = website_link
          artist.facebook_link = facebook_link
          artist.genres = []
          
          for genre in genres:
              fetch_genre = Genre.query.filter_by(name=genre).one_or_none() 
              if fetch_genre:
                  artist.genres.append(fetch_genre)

              else:
                  new_genre = Genre(name=genre)
                  db.session.add(new_genre)
                  artist.genres.append(new_genre) 

          db.session.commit()
      except Exception as e:
          update_error = True
          print(f'Exception "{e}" in editing artist info')
          db.session.rollback()
      finally:
          db.session.close()

      if not update_error:
          flash('Artist ' + request.form['name'] + ' successfully updated!')
          return redirect(url_for('show_artist', artist_id=artist_id))
      else:
          flash('An error occurred. Artist ' + name + ' could not be updated.')
          print("Error while updating artist")
          abort(500)

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)  
  if not venue:
      return redirect(url_for('index'))
  else:
      form = VenueForm(obj=venue)

  genres = [ genre.name for genre in venue.genres ]
    
  venue={
    "id": venue_id,
    "name": venue.name,
    "genres": genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": (venue.phone[:3] + '-' + venue.phone[3:6] + '-' + venue.phone[6:]),
    "website_link": venue.website_link,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  }

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  form = VenueForm()
  
  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  address = form.address.data.strip()
  phone = form.phone.data
  phone = re.sub('\D', '', phone) 
  genres = form.genres.data                  
  seeking_talent = True if form.seeking_talent.data == 'Yes' else False
  seeking_description = form.seeking_description.data.strip()
  image_link = form.image_link.data.strip()
  website_link = form.website_link.data.strip()
  facebook_link = form.facebook_link.data.strip()
    
  if not form.validate():
      flash( form.errors )
      return redirect(url_for('edit_venue_submission', venue_id=venue_id))

  else:
      update_error = False
      try:
          venue = Venue.query.get(venue_id)
          venue.name = name
          venue.city = city
          venue.state = state
          venue.address = address
          venue.phone = phone
          venue.seeking_talent = seeking_talent
          venue.seeking_description = seeking_description
          venue.image_link = image_link
          venue.website_link = website_link
          venue.facebook_link = facebook_link
          venue.genres = []
            
          for genre in genres:
              fetch_genre = Genre.query.filter_by(name=genre).one_or_none() 
              if fetch_genre:
                  venue.genres.append(fetch_genre)
              else:
                  new_genre = Genre(name=genre)
                  db.session.add(new_genre)
                  venue.genres.append(new_genre)  


          db.session.commit()
      except Exception as e:
          update_error = True
          print(f'Exception "{e}" while editing venue')
          db.session.rollback()
      finally:
          db.session.close()

      if not update_error:
          flash('Venue ' + request.form['name'] + ' successfully updated!')
          return redirect(url_for('show_venue', venue_id=venue_id))
      else:
          flash('An error happened. Venue ' + name + ' could not be updated.')
          print("Error while editing the venuw")
          abort(500)


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  form = ArtistForm()
  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  phone = form.phone.data
  phone = re.sub('\D', '', phone) 
  genres = form.genres.data                   
  seeking_venue = True if form.seeking_venue.data == 'Yes' else False
  seeking_description = form.seeking_description.data.strip()
  image_link = form.image_link.data.strip()
  website_link = form.website_link.data.strip()
  facebook_link = form.facebook_link.data.strip()
  
  if not form.validate():
      flash( form.errors )
      return redirect(url_for('create_artist_submission'))

  else:
      insertion_error = False
      try:
          new_artist = Artist(name=name, city=city, state=state, phone=phone, \
              seeking_venue=seeking_venue, seeking_description=seeking_description, image_link=image_link, \
              website_link=website_link, facebook_link=facebook_link)
          for genre in genres:
              fetch_genre = Genre.query.filter_by(name=genre).one_or_none() 
              if fetch_genre:
                  new_artist.genres.append(fetch_genre)
              else:
                  new_genre = Genre(name=genre)
                  db.session.add(new_genre)
                  new_artist.genres.append(new_genre)  
          db.session.add(new_artist)
          db.session.commit()
      except Exception as e:
          insertion_error = True
          print(f'Exception "{e}" in create_artist_submission()')
          db.session.rollback()
      finally:
          db.session.close()

      if not insertion_error:
          flash('Artist ' + request.form['name'] + ' was successfully listed!')
          return redirect(url_for('index'))
      else:
          flash('An error occurred. Artist ' + name + ' could not be listed.')
          print("Error in create_artist_submission()")
          abort()

  

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = []
  shows = Show.query.all()
  
  for show in shows:
      data.append({
          "venue_id": show.venue.id,
          "venue_name": show.venue.name,
          "artist_id": show.artist.id,
          "artist_name": show.artist.name,
          "artist_image_link": show.artist.image_link,
          "starting_time": format_datetime(str(show.starting_time))
      })

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  form = ShowForm()
  artist_id = form.artist_id.data.strip()
  venue_id = form.venue_id.data.strip()
  starting_time = form.starting_time.data

  error_in_insert = False
  
  try:
      new_show = Show(starting_time=starting_time, artist_id=artist_id, venue_id=venue_id)
      db.session.add(new_show)
      db.session.commit()
  except Exception as e:
      error_in_insert = True
      print(f'Exception "{e}" in create_show_submission()')
      db.session.rollback()
  finally:
      db.session.close()

  if error_in_insert:
      flash(f'An error happened.  Show could not be created.')
      print("Error while creating a show")
  else:
      flash('Show was successfully listed!')
  
  return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
