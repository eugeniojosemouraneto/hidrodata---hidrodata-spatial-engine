from django import forms


class SpatialSearchForm(forms.Form):

    latitude = forms.FloatField(
        label='Latitude',
        widget=forms.NumberInput(
            attrs={
                'id': 'id_latitude', 
                'class': 'form-control', 
                'step': 'any', 
                'placeholder': 'Ex: -15.78'
            }
        )
    )

    longitude = forms.FloatField(
        label="Longitude",
        widget=forms.NumberInput(
            attrs={
                'id': 'id_longitude', 
                'class': 'form-control', 
                'step': 'any', 
                'placeholder': 'Ex: -47.92'
            }
        )
    )

    radius_kilometers = forms.FloatField(
        label="Raio de Busca (km)",
        initial=50.0,
        min_value=20.0, 
        max_value=125.0,
        help_text="Mínimo: 20 km | Máximo: 125 km.", 
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control', 
                'min': '20',  
                'max': '125',  
                'step': '0.1'
            }
        )
    )

    limit_per_quadrant = forms.IntegerField(
        label="Limite por Quadrante",
        initial=3,
        min_value=1, 
        max_value=5,
        help_text="De 1 a 5 estações por área.", 
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control', 
                'min': '1',  
                'max': '5',  
                'step': '1'
            }
        )
    )

    def clean(self):
        cleaned_data = super().clean()

        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')

        if latitude is not None and longitude is not None:
            LATITUDE_MIN, LATITUDE_MAX = -33.75, 5.27
            LONGITUDE_MIN, LONGITUDE_MAX = -73.99, -34.79

            if not (LATITUDE_MIN <= latitude <= LATITUDE_MAX and LONGITUDE_MIN <= longitude <= LONGITUDE_MAX):
                raise forms.ValidationError(
                    "Coordenada inválida! O ponto selecionado está fora do território brasileiro."
                )
        
        return cleaned_data