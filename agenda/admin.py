from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from models import *

from sorl.thumbnail.admin import AdminInlineImageMixin
from sorl.thumbnail import get_thumbnail

from utils import ExtendibleModelAdminMixin

from tinymce.widgets import TinyMCE
from tinymce.views import render_to_image_list, render_to_link_list

class MediaAdminMixin(object):
    def get_image_list(self, request, object_id):
        """ Get a list of available images for this page for TinyMCE to
            refer to. If the setting exists, scale the image to the default
            size specified in `PAGEIMAGE_SIZE`.
        """
        object = self._getobj(request, object_id)
        
        images = object.eventimage_set.all()
    
        image_list = []
        for obj in images:
            image = obj.image
            if settings.PAGEIMAGE_SIZE:
                image = get_thumbnail(image, settings.PAGEIMAGE_SIZE)
        
            image_list.append((unicode(obj), image.url))
        
        return render_to_image_list(image_list)
    
    def get_link_list(self, request, object_id):
        """ Get a list of pages and their URL's.
            TODO: Filter out the current page, if applicable.
        """

        object = self._getobj(request, object_id)
                
        pages = self.model.objects.filter(publish=True)
        
        # # Exclude the current page, if it exists at all
        # if object.pk:
        #     pages = pages.exclude(pk=object.pk)
        
        link_list = []
        for page in pages:
            url = page.get_absolute_url()
            
            if url:
                link_list.append((page.title, url))


        files = object.eventfile_set.all()

        for obj in files:
            file = obj.file
            link_list.append((unicode(obj), file.url))
         
        return render_to_link_list(link_list)


class TinyMCEAdminMixin(object):
    @staticmethod
    def get_tinymce_widget(obj=None):
        """ Return the appropriate TinyMCE widget. """

        link_list_url = None
        if obj:
            link_list_url = reverse('admin:agenda_event_link_list', args=(obj.pk, ))
            image_list_url = reverse('admin:agenda_event_image_list',\
                                     args=(obj.pk, ))
            return \
               TinyMCE(mce_attrs={'external_image_list_url': image_list_url,
                                  'external_link_list_url': link_list_url})
        else:
            return \
               TinyMCE(mce_attrs={'external_link_list_url': link_list_url})

class EventImageInline(AdminInlineImageMixin, admin.TabularInline):
    model = EventImage
    extra = 1


class EventFileInline(admin.TabularInline):
    model = EventFile
    extra = 1

class LocationAdmin(admin.ModelAdmin):
    list_display = ('title', )
    
    prepopulated_fields = {"slug": ("title",)}
    
admin.site.register(Location, LocationAdmin)

class EventAdmin(TinyMCEAdminMixin, MediaAdminMixin, ExtendibleModelAdminMixin, admin.ModelAdmin):
    inlines = (EventImageInline, EventFileInline)
    list_display = ('title', 'author', 'event_date', 'start_time', 'location', 'publish', 'calendar')
    list_display_links = ('title', )
    list_filter = ('event_date', 'publish', 'author', 'location', 'calendar')

    date_hierarchy = 'event_date'
    
    prepopulated_fields = {"slug": ("title",)}
    
    search_fields = ('title', 'location__title', 'author__username', 'author__first_name', 'author__last_name', 'calendar')        

    fieldsets =  ((None, {'fields': ['title', 'slug', 'event_date', 'start_time', 'end_time', 'location', 'description', 'calendar',]}),
                  (_('Advanced options'), {'classes' : ('collapse',),
                                           'fields'  : ('publish_date', 'publish', 'sites', 'author', 'allow_comments')}))
    
    # This is a dirty hack, this belongs inside of the model but defaults don't work on M2M
    def formfield_for_dbfield(self, db_field, **kwargs):
        """ Makes sure that by default all sites are selected. """
        if db_field.name == 'sites': # Check if it's the one you want
            kwargs.update({'initial': Site.objects.all()})
         
        return super(EventAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        """ Override the form widget for the content field with a TinyMCE
            field which uses a dynamically assigned image list. """

        form = super(TinyMCEAdminMixin, self).get_form(request, obj=None, **kwargs)
        
        form.base_fields['description'].widget = self.get_tinymce_widget(obj)

        return form

    def get_urls(self):
        urls = super(EventAdmin, self).get_urls()
        
        my_urls = patterns('',
            url(r'^(.+)/image_list.js$', 
                self._wrap(self.get_image_list), 
                name=self._view_name('image_list')),
            url(r'^(.+)/link_list.js$', 
                self._wrap(self.get_link_list), 
                name=self._view_name('link_list')),
        )

        return my_urls + urls
    
admin.site.register(Event, EventAdmin)

admin.site.register(Calendar)
